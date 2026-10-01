from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class KBChunk(BaseModel):
    chunk_id: str
    title: str
    category: str  # "products", "policies", "faqs", "rates", "objections"
    source_file: str
    content: str
    keywords: List[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    chunk: KBChunk
    score: float
    citation: str  # e.g. "Darwix KB: loan_products.md (darwix-term-loan)"


class RetrievalResponse(BaseModel):
    has_match: bool
    query: str
    best_chunk: Optional[KBChunk] = None
    confidence_score: float = 0.0
    citation: Optional[str] = None
    voice_answer: str
