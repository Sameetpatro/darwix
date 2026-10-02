import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END

from q2.models.raw_document import RawDocument
from q2.parsers.pdf_parser import PDFParser
from q2.parsers.html_parser import HTMLParser
from q2.parsers.table_parser import TableParser
from q2.parsers.text_parser import TextParser
from q2.classification.laya_client import laya_classifier
from app.logging_config import logger


class IngestionState(TypedDict):
    """LangGraph State representation for document ingestion workflow."""
    file_path: str
    source_type: str
    selected_parser: Optional[str]
    extracted_documents: List[RawDocument]
    validation_status: str  # 'valid', 'invalid', 'empty', 'error'
    retry_count: int
    error_message: Optional[str]
    flagged_for_manual_review: bool
    stored_path: Optional[str]


# Parser registry
PARSER_REGISTRY = {
    "pdf": PDFParser(),
    "html": HTMLParser(),
    "csv": TableParser(),
    "table": TableParser(),
    "text": TextParser(),
}


# =====================================================================
# Node 1: Identify Source
# =====================================================================
def identify_source_node(state: IngestionState) -> Dict[str, Any]:
    path = Path(state["file_path"])
    ext = path.suffix.lower()

    if ext == ".pdf":
        source_type = "pdf"
    elif ext in [".html", ".htm", ".xhtml"]:
        source_type = "html"
    elif ext in [".csv", ".tsv"]:
        source_type = "csv"
    elif ext in [".txt", ".md", ".text"]:
        source_type = "text"
    else:
        # Inspect magic bytes for sniffing
        source_type = "unknown"
        if path.exists():
            try:
                with open(path, "rb") as f:
                    header = f.read(512)
                if header.startswith(b"%PDF"):
                    source_type = "pdf"
                elif b"<html" in header.lower() or b"<!doctype html" in header.lower():
                    source_type = "html"
                elif b"," in header and b"\n" in header:
                    source_type = "csv"
            except Exception:
                pass

    logger.info("[INGESTION-GRAPH] Identified source for '%s' -> %s", path.name, source_type)
    return {"source_type": source_type}


# =====================================================================
# Node 2: Select Parser
# =====================================================================
def select_parser_node(state: IngestionState) -> Dict[str, Any]:
    source_type = state["source_type"]
    if source_type in PARSER_REGISTRY:
        selected = source_type
    else:
        selected = None
    logger.info("[INGESTION-GRAPH] Selected parser: %s", selected)
    return {"selected_parser": selected}


# =====================================================================
# Node 3: Extract Content
# =====================================================================
def extract_content_node(state: IngestionState) -> Dict[str, Any]:
    parser_key = state.get("selected_parser")
    path = Path(state["file_path"])

    if not parser_key or parser_key not in PARSER_REGISTRY:
        return {
            "extracted_documents": [],
            "error_message": f"No suitable parser found for source_type: {state['source_type']}",
            "validation_status": "error",
        }

    parser = PARSER_REGISTRY[parser_key]
    try:
        docs = parser.parse(path)
        return {"extracted_documents": docs, "error_message": None}
    except Exception as exc:
        logger.error("[INGESTION-GRAPH] Extraction error with %s: %s", parser_key, exc)
        return {
            "extracted_documents": [],
            "error_message": str(exc),
            "validation_status": "error",
        }


# =====================================================================
# Node 4: Validate Extraction
# =====================================================================
def validate_extraction_node(state: IngestionState) -> Dict[str, Any]:
    docs = state.get("extracted_documents", [])
    if not docs:
        return {"validation_status": "empty"}

    valid_count = sum(1 for d in docs if d.raw_content and len(d.raw_content.strip()) > 15 and d.extraction_status != "failed")
    if valid_count > 0:
        return {"validation_status": "valid"}
    else:
        return {"validation_status": "invalid"}


# =====================================================================
# Conditional Edge: Check Validation Status
# =====================================================================
def check_validation_condition(state: IngestionState) -> str:
    status = state.get("validation_status")
    retry_count = state.get("retry_count", 0)

    if status == "valid":
        return "classify"
    elif retry_count == 0:
        return "retry"
    else:
        return "flag"


# =====================================================================
# Node 5: Retry / Alternate Parser
# =====================================================================
def retry_alternate_parser_node(state: IngestionState) -> Dict[str, Any]:
    path = Path(state["file_path"])
    logger.warning("[INGESTION-GRAPH] Extraction failed/empty. Attempting alternate fallback parser on %s", path.name)

    # Alternate parser: Raw byte stream string recovery
    try:
        with open(path, "rb") as f:
            raw_bytes = f.read()

        # Extract printable ASCII/UTF-8 strings
        decoded = raw_bytes.decode("utf-8", errors="ignore")
        clean_text = "\n".join(line.strip() for line in decoded.splitlines() if len(line.strip()) > 10)

        if len(clean_text) > 30:
            doc = RawDocument(
                source_type=state.get("source_type", "unknown"),
                source=path.name,
                page=1,
                title=f"{path.stem.title()} (Recovered Stream)",
                raw_content=clean_text,
                extraction_status="retry_succeeded",
                metadata={"recovered_via": "byte_stream_decoder"},
            )
            return {
                "extracted_documents": [doc],
                "retry_count": state.get("retry_count", 0) + 1,
                "validation_status": "valid",
                "error_message": None,
            }
    except Exception as exc:
        logger.error("[INGESTION-GRAPH] Retry alternate parser failed: %s", exc)

    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "validation_status": "failed",
    }


# =====================================================================
# Node 6: Flag for Manual Review
# =====================================================================
def flag_for_review_node(state: IngestionState) -> Dict[str, Any]:
    path = Path(state["file_path"])
    err = state.get("error_message") or "Extraction produced empty content after parser retry"
    logger.error("[INGESTION-GRAPH] FLAGGING FOR MANUAL REVIEW: %s | Reason: %s", path.name, err)

    flagged_doc = RawDocument(
        source_type=state.get("source_type", "unknown"),
        source=path.name,
        page=1,
        title=f"FLAGGED: {path.stem.title()}",
        raw_content="",
        extraction_status="flagged_for_review",
        metadata={
            "flagged_for_manual_review": True,
            "error_reason": err,
            "file_size": path.stat().st_size if path.exists() else 0,
        },
    )
    return {
        "flagged_for_manual_review": True,
        "extracted_documents": [flagged_doc],
    }


# =====================================================================
# Node 7: Classify Content (Jev / Laya)
# =====================================================================
def classify_content_node(state: IngestionState) -> Dict[str, Any]:
    docs = state.get("extracted_documents", [])
    classified_docs = []

    for doc in docs:
        if doc.raw_content and doc.extraction_status != "flagged_for_review":
            cat, conf = laya_classifier.classify_content(doc.raw_content)
            doc.content_type = cat
            doc.classification_confidence = conf
        classified_docs.append(doc)

    return {"extracted_documents": classified_docs}


# =====================================================================
# Node 8: Store Raw Document
# =====================================================================
def store_raw_document_node(state: IngestionState) -> Dict[str, Any]:
    path = Path(state["file_path"])
    docs = state.get("extracted_documents", [])
    output_dir = Path("data/raw_extracted")
    output_dir.mkdir(parents=True, exist_ok=True)

    out_file = output_dir / f"{path.stem}_extracted.json"
    data = {
        "source_file": path.name,
        "source_type": state.get("source_type"),
        "total_documents": len(docs),
        "flagged_for_review": state.get("flagged_for_manual_review", False),
        "documents": [d.to_dict() for d in docs],
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    logger.info("[INGESTION-GRAPH] Stored %d raw document sections in %s", len(docs), out_file)
    return {"stored_path": str(out_file)}


# =====================================================================
# Build and Compile the LangGraph
# =====================================================================
def create_ingestion_graph():
    workflow = StateGraph(IngestionState)

    # Add Nodes
    workflow.add_node("identify_source", identify_source_node)
    workflow.add_node("select_parser", select_parser_node)
    workflow.add_node("extract_content", extract_content_node)
    workflow.add_node("validate_extraction", validate_extraction_node)
    workflow.add_node("retry_alternate_parser", retry_alternate_parser_node)
    workflow.add_node("flag_for_review", flag_for_review_node)
    workflow.add_node("classify_content", classify_content_node)
    workflow.add_node("store_raw_document", store_raw_document_node)

    # Add Edges
    workflow.add_edge(START, "identify_source")
    workflow.add_edge("identify_source", "select_parser")
    workflow.add_edge("select_parser", "extract_content")
    workflow.add_edge("extract_content", "validate_extraction")

    # Conditional Branching
    workflow.add_conditional_edges(
        "validate_extraction",
        check_validation_condition,
        {
            "classify": "classify_content",
            "retry": "retry_alternate_parser",
            "flag": "flag_for_review",
        },
    )

    workflow.add_edge("retry_alternate_parser", "validate_extraction")
    workflow.add_edge("flag_for_review", "store_raw_document")
    workflow.add_edge("classify_content", "store_raw_document")
    workflow.add_edge("store_raw_document", END)

    return workflow.compile()


ingestion_graph = create_ingestion_graph()


def ingest_file(file_path: str) -> IngestionState:
    """Convenience helper to run a single file through the LangGraph ingestion pipeline."""
    initial_state: IngestionState = {
        "file_path": str(file_path),
        "source_type": "unknown",
        "selected_parser": None,
        "extracted_documents": [],
        "validation_status": "started",
        "retry_count": 0,
        "error_message": None,
        "flagged_for_manual_review": False,
        "stored_path": None,
    }
    return ingestion_graph.invoke(initial_state)
