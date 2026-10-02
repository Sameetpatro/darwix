from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import time
import uuid

from q2.models.knowledge_record import ConflictRecord


class KnowledgeChunk(BaseModel):
    """
    Standardized semantic chunk for dense vector indexing and sparse BM25 retrieval.
    Includes contextual prefix headers to preserve document, section, and product provenance.
    """
    chunk_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:10]}")
    record_id: str = Field(..., description="Parent KnowledgeRecord ID")
    chunk_index: int = Field(0, description="0-indexed position within parent document")
    title: str = Field(..., description="Document or section heading")
    content: str = Field(..., description="Chunk content body")
    context_header: str = Field(..., description="Provenance prefix, e.g. [Document: ...] [Product: ...]")
    category: str = Field("other", description="qualification, product, policy, faq, objection, other")
    product: Optional[str] = Field(None, description="Standardized loan product name")
    source: str = Field(..., description="Original filename or URL")
    source_location: Dict[str, Any] = Field(default_factory=dict, description="page, section, table_id, row")
    embedding: Optional[List[float]] = Field(None, description="Dense vector embedding (384-dim for BGE)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Word count, conflict count, version")
    created_at: float = Field(default_factory=time.time)

    @property
    def full_context_text(self) -> str:
        """Returns the full searchable string with contextual header."""
        return f"{self.context_header}\n{self.content}".strip()

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class SearchResult(BaseModel):
    """
    Unified result object returned by the hybrid retrieval engine.
    """
    chunk: KnowledgeChunk
    dense_score: float = 0.0
    sparse_score: float = 0.0
    fused_score: float = 0.0
    rank: int = 1
    conflicts: List[ConflictRecord] = Field(default_factory=list)
