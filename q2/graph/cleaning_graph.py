from typing import TypedDict, List, Dict, Any, Optional
import hashlib
from langgraph.graph import StateGraph, START, END

from q2.models.raw_document import RawDocument
from q2.models.knowledge_record import KnowledgeRecord, NormalizedEntities, ConflictRecord
from q2.cleaning.boilerplate import clean_boilerplate
from q2.pii.redactor import pii_redactor
from q2.normalization.normalizer import entity_normalizer
from q2.deduplication.deduplicator import deduplicator
from q2.conflicts.conflict_detector import conflict_detector
from q2.classification.laya_client import laya_classifier
from q2.storage.knowledge_store import knowledge_store
from app.logging_config import logger


class CleaningState(TypedDict):
    raw_document: RawDocument
    cleaned_text: str
    removed_noise: List[str]
    redacted_text: str
    pii_audit: Dict[str, int]
    normalized_entities: Optional[NormalizedEntities]
    is_duplicate: bool
    duplicate_of: Optional[str]
    cleaned_content_hash: str
    conflicts: List[ConflictRecord]
    category: str
    product: Optional[str]
    knowledge_record: Optional[KnowledgeRecord]
    stored_path: Optional[str]
    status: str
    errors: List[str]


def clean_text_node(state: CleaningState) -> Dict[str, Any]:
    """Node 1: Removes HTML noise, banners, footers, and normalizes unicode."""
    raw_text = state["raw_document"].raw_content
    cleaned, noise = clean_boilerplate(raw_text)
    return {
        "cleaned_text": cleaned,
        "removed_noise": noise,
    }


def redact_pii_node(state: CleaningState) -> Dict[str, Any]:
    """Node 2: Scans and redacts PII (SSN, EIN, phones, emails, bank accounts, names)."""
    cleaned = state["cleaned_text"]
    redacted, audit = pii_redactor.redact(cleaned)
    return {
        "redacted_text": redacted,
        "pii_audit": audit,
    }


def normalize_node(state: CleaningState) -> Dict[str, Any]:
    """Node 3: Normalizes business operating history, currency values, dates, and products."""
    text = state["redacted_text"]
    entities = entity_normalizer.normalize(text)
    
    # Determine primary product
    product = None
    if entities.loan_products:
        product = entities.loan_products[0]
    elif state["raw_document"].section and any(p.lower() in state["raw_document"].section.lower() for p in ["term loan", "line of credit", "equipment financing", "sba"]):
        for p in ["Term Loan", "Line of Credit", "Equipment Financing", "SBA 7(a) Loan"]:
            if p.lower() in state["raw_document"].section.lower():
                product = p
                break

    return {
        "normalized_entities": entities,
        "product": product,
    }


def deduplicate_node(state: CleaningState) -> Dict[str, Any]:
    """Node 4: Checks for exact and near-duplicates (>85% token overlap)."""
    text = state["redacted_text"]
    doc_id = state["raw_document"].document_id
    
    is_dup, dup_of, sim, content_hash = deduplicator.check_and_register(doc_id, text)
    return {
        "is_duplicate": is_dup,
        "duplicate_of": dup_of,
        "cleaned_content_hash": content_hash,
    }


def detect_conflicts_node(state: CleaningState) -> Dict[str, Any]:
    """Node 5: Scans business constraints against registry for policy discrepancies."""
    doc_id = state["raw_document"].document_id
    title = state["raw_document"].title
    product = state["product"]
    entities = state["normalized_entities"] or NormalizedEntities()
    source = state["raw_document"].source

    conflicts = conflict_detector.detect_conflicts(
        record_id=doc_id,
        title=title,
        product=product,
        entities=entities,
        source=source,
    )
    return {
        "conflicts": conflicts,
    }


def classify_and_structure_node(state: CleaningState) -> Dict[str, Any]:
    """Node 6: Refines category with Laya if needed, creates and persists KnowledgeRecord."""
    raw_doc = state["raw_document"]
    text = state["redacted_text"]
    
    # Check if category needs confirmation or refinement
    category = raw_doc.content_type
    if category == "other" or raw_doc.classification_confidence < 0.2:
        cat, conf = laya_classifier.classify_content(text[:500])
        category = cat

    # Compute raw content hash
    raw_hash = hashlib.sha256(raw_doc.raw_content.encode("utf-8")).hexdigest()

    record = KnowledgeRecord(
        source_doc_id=raw_doc.document_id,
        title=raw_doc.title,
        cleaned_content=text,
        original_content_hash=raw_hash,
        cleaned_content_hash=state["cleaned_content_hash"],
        category=category,
        product=state["product"],
        source=raw_doc.source,
        source_location={
            "page": raw_doc.page,
            "section": raw_doc.section,
        },
        version=raw_doc.metadata.get("version", "1.0"),
        effective_date=state["normalized_entities"].normalized_dates[0] if (state["normalized_entities"] and state["normalized_entities"].normalized_dates) else None,
        normalized_entities=state["normalized_entities"] or NormalizedEntities(),
        pii_audit=state["pii_audit"],
        conflicts=state["conflicts"],
        is_duplicate=state["is_duplicate"],
        duplicate_of=state["duplicate_of"],
    )

    # Persist
    stored_path = knowledge_store.save_record(record)
    logger.info("[CLEANING-GRAPH] Stored KnowledgeRecord %s (category=%s, product=%s)", record.record_id, category, record.product)

    return {
        "category": category,
        "knowledge_record": record,
        "stored_path": stored_path,
        "status": "success",
    }


def should_continue_after_cleaning(state: CleaningState) -> str:
    """Conditional check: ensures text is not completely empty after boilerplate strip."""
    if not state["cleaned_text"].strip():
        return "empty"
    return "proceed"


def empty_text_fallback_node(state: CleaningState) -> Dict[str, Any]:
    """Handles documents that became empty after noise stripping."""
    return {
        "status": "failed",
        "errors": ["Text became empty after boilerplate removal"],
        "knowledge_record": None,
        "stored_path": None,
    }


def build_cleaning_graph() -> StateGraph:
    """Constructs the LangGraph Cleaning, PII, Normalization & Structuring Graph."""
    workflow = StateGraph(CleaningState)

    # Add Nodes
    workflow.add_node("clean_text", clean_text_node)
    workflow.add_node("empty_fallback", empty_text_fallback_node)
    workflow.add_node("redact_pii", redact_pii_node)
    workflow.add_node("normalize", normalize_node)
    workflow.add_node("deduplicate", deduplicate_node)
    workflow.add_node("detect_conflicts", detect_conflicts_node)
    workflow.add_node("classify_and_structure", classify_and_structure_node)

    # Edges
    workflow.add_edge(START, "clean_text")
    workflow.add_conditional_edges(
        "clean_text",
        should_continue_after_cleaning,
        {
            "proceed": "redact_pii",
            "empty": "empty_fallback",
        },
    )
    workflow.add_edge("empty_fallback", END)
    workflow.add_edge("redact_pii", "normalize")
    workflow.add_edge("normalize", "deduplicate")
    workflow.add_edge("deduplicate", "detect_conflicts")
    workflow.add_edge("detect_conflicts", "classify_and_structure")
    workflow.add_edge("classify_and_structure", END)

    return workflow.compile()


cleaning_graph = build_cleaning_graph()


def clean_and_structure_document(raw_doc: RawDocument) -> Dict[str, Any]:
    """
    Executes the LangGraph cleaning workflow on a single RawDocument.
    """
    initial_state: CleaningState = {
        "raw_document": raw_doc,
        "cleaned_text": "",
        "removed_noise": [],
        "redacted_text": "",
        "pii_audit": {},
        "normalized_entities": None,
        "is_duplicate": False,
        "duplicate_of": None,
        "cleaned_content_hash": "",
        "conflicts": [],
        "category": raw_doc.content_type,
        "product": None,
        "knowledge_record": None,
        "stored_path": None,
        "status": "pending",
        "errors": [],
    }

    return cleaning_graph.invoke(initial_state)


def process_raw_documents(raw_docs: List[RawDocument]) -> List[KnowledgeRecord]:
    """
    Processes a list of RawDocuments through the cleaning graph and returns
    all resulting KnowledgeRecords.
    """
    records = []
    for doc in raw_docs:
        res = clean_and_structure_document(doc)
        if res.get("knowledge_record"):
            records.append(res["knowledge_record"])
    return records
