import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from q2.models.chunk import SearchResult
from q2.retrieval.hybrid_search import hybrid_search_engine
from app.logging_config import logger

router = APIRouter(prefix="/retrieve", tags=["Knowledge Retrieval"])


class RetrieveRequest(BaseModel):
    query: str = Field(..., description="User question or semantic search query")
    top_k: Optional[int] = Field(3, description="Number of evidence chunks to retrieve", ge=1, le=10)
    category: Optional[str] = Field(None, description="Filter by category: qualification, product, policy, faq, objection")
    product: Optional[str] = Field(None, description="Filter by product: Term Loan, Line of Credit, Equipment Financing, etc.")
    customer_context: Optional[Dict[str, Any]] = Field(None, description="Optional caller profile: credit_score, time_in_business, revenue")
    dense_weight: Optional[float] = Field(0.6, description="Weight for dense vector similarity in RRF")
    sparse_weight: Optional[float] = Field(0.4, description="Weight for sparse BM25 similarity in RRF")


class EvidenceItem(BaseModel):
    chunk_id: str
    title: str
    content: str
    citation: str
    source: str
    source_location: Dict[str, Any]
    category: str
    product: Optional[str]
    score: float
    dense_score: float
    sparse_score: float
    has_conflict: bool
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)


class RetrieveResponse(BaseModel):
    query: str
    results_count: int
    evidence: List[EvidenceItem]
    synthesized_context: str
    latency_ms: float


def format_citation(source: str, title: str, location: Dict[str, Any]) -> str:
    """Formats human-readable and auditable citation."""
    loc_parts = []
    if "page" in location and location["page"]:
        loc_parts.append(f"Page {location['page']}")
    if "section" in location and location["section"]:
        loc_parts.append(f"{location['section']}")

    loc_str = f", {', '.join(loc_parts)}" if loc_parts else ""
    return f"[{source}{loc_str} | '{title}']"


def rerank_with_context(
    results: List[SearchResult], customer_context: Optional[Dict[str, Any]]
) -> List[SearchResult]:
    """
    Adjusts candidate ranking based on active borrower qualification profile:
    e.g. boosts Prime Tier for credit score >= 680, or boosts Alternative Working Capital for credit score < 600.
    """
    if not customer_context or not results:
        return results

    cs = customer_context.get("credit_score")
    tib = customer_context.get("time_in_business") or customer_context.get("time_in_business_months")
    rev = customer_context.get("monthly_revenue")

    boosted = []
    for r in results:
        boost = 1.0
        content_lower = r.chunk.content.lower()

        # Credit Score alignment
        if cs is not None:
            if cs >= 680 and ("prime" in content_lower or "tier 1" in content_lower):
                boost *= 1.25
            elif cs < 620 and ("alternative" in content_lower or "tier 3" in content_lower or "subprime" in content_lower):
                boost *= 1.25

        # Operating history alignment
        if tib is not None:
            if tib < 12 and ("short-term" in content_lower or "working capital" in content_lower or "6 months" in content_lower):
                boost *= 1.20
            elif tib >= 24 and ("term loan" in content_lower or "prime" in content_lower):
                boost *= 1.15

        # Monthly revenue alignment
        if rev is not None and rev >= 30000 and "prime" in content_lower:
            boost *= 1.15

        boosted.append((r, r.fused_score * boost))

    boosted.sort(key=lambda x: x[1], reverse=True)
    return [item[0] for item in boosted]


@router.post("", response_model=RetrieveResponse)
async def retrieve_evidence(req: RetrieveRequest) -> RetrieveResponse:
    """
    Main Enterprise RAG Retrieval Endpoint:
    Executes dense vector (Neon pgvector) + sparse BM25 hybrid search with RRF fusion,
    applies customer qualification context reranking, and returns structured citations.
    """
    start_time = time.time()
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    try:
        # 1. Execute Hybrid Search
        results = hybrid_search_engine.search(
            query=query,
            top_k=req.top_k * 2 if req.customer_context else req.top_k,
            category=req.category,
            product=req.product,
            dense_weight=req.dense_weight,
            sparse_weight=req.sparse_weight,
        )

        # 2. Context-aware Re-ranking
        if req.customer_context:
            results = rerank_with_context(results, req.customer_context)[:req.top_k]
        else:
            results = results[:req.top_k]

        # 3. Assemble Evidence Items & Synthesized Prompt Context
        evidence_items: List[EvidenceItem] = []
        context_blocks: List[str] = []

        for idx, r in enumerate(results):
            citation = format_citation(r.chunk.source, r.chunk.title, r.chunk.source_location)
            has_conf = len(r.conflicts) > 0
            conf_dicts = [c.model_dump() for c in r.conflicts]

            item = EvidenceItem(
                chunk_id=r.chunk.chunk_id,
                title=r.chunk.title,
                content=r.chunk.content,
                citation=citation,
                source=r.chunk.source,
                source_location=r.chunk.source_location,
                category=r.chunk.category,
                product=r.chunk.product,
                score=r.fused_score,
                dense_score=r.dense_score,
                sparse_score=r.sparse_score,
                has_conflict=has_conf,
                conflicts=conf_dicts,
            )
            evidence_items.append(item)

            # Build synthesized context block
            conflict_warning = ""
            if has_conf:
                conflict_desc = "; ".join([c["description"] for c in conf_dicts])
                conflict_warning = f"\n[NOTE ON POLICY DISCREPANCY: {conflict_desc}]"

            block = (
                f"[Evidence {idx + 1}] Citation: {citation}\n"
                f"Category: {r.chunk.category} | Product: {r.chunk.product or 'General'}\n"
                f"{r.chunk.content}{conflict_warning}"
            )
            context_blocks.append(block)

        synthesized = "\n\n---\n\n".join(context_blocks)
        latency = round((time.time() - start_time) * 1000, 2)

        logger.info(
            "[RETRIEVE-API] Query: '%s' -> %d items in %.2fms",
            query[:50],
            len(evidence_items),
            latency,
        )

        return RetrieveResponse(
            query=query,
            results_count=len(evidence_items),
            evidence=evidence_items,
            synthesized_context=synthesized,
            latency_ms=latency,
        )

    except Exception as exc:
        logger.error("[RETRIEVE-API] Retrieval failed for query '%s': %s", query[:50], exc)
        raise HTTPException(status_code=500, detail=f"Knowledge retrieval error: {str(exc)}")
