from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import time
import uuid


class TableData(BaseModel):
    """Represents a structured table extracted from a document."""
    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)
    row_count: int = 0
    column_count: int = 0


class RawDocument(BaseModel):
    """
    Standardized Raw Document schema for Q2 ingestion.
    Preserves complete provenance, heading/section context, and Laya classification.
    """
    document_id: str = Field(default_factory=lambda: f"doc_{uuid.uuid4().hex[:10]}")
    source_type: str = Field(..., description="pdf, html, csv, table, text, structured, unknown")
    source: str = Field(..., description="Original filename or URL")
    page: Optional[int] = Field(None, description="1-indexed page number for multi-page documents (PDFs)")
    section: Optional[str] = Field(None, description="Detected section or subsection name")
    title: str = Field(..., description="Heading or document title")
    raw_content: str = Field(..., description="Extracted raw text content")
    tables: List[TableData] = Field(default_factory=list, description="Extracted structured tables if any")
    extraction_status: str = Field("success", description="success, retry_succeeded, failed, flagged_for_review")
    content_type: str = Field("other", description="product, qualification, policy, faq, objection, marketing, other")
    classification_confidence: float = Field(0.0, description="Confidence score from Laya or classifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Parser details, timestamps, word counts")
    created_at: float = Field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class IngestionBatch(BaseModel):
    """Container for batch ingestion results."""
    batch_id: str = Field(default_factory=lambda: f"batch_{uuid.uuid4().hex[:8]}")
    source_file: str
    total_documents: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    flagged_for_review: int = 0
    documents: List[RawDocument] = Field(default_factory=list)
