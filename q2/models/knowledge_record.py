from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import time
import uuid


class ConflictRecord(BaseModel):
    """
    Represents a detected contradiction or policy divergence between knowledge records.
    Allows downstream RAG to provide accurate, nuanced answers rather than hallucinating.
    """
    conflict_id: str = Field(default_factory=lambda: f"conf_{uuid.uuid4().hex[:8]}")
    field: str = Field(..., description="The conflicting attribute, e.g. min_months_in_business, min_credit_score")
    product: str = Field(..., description="Product or policy name, e.g. Term Loan, General Eligibility")
    conflicting_record_id: str = Field(..., description="ID of the opposing knowledge record")
    this_value: Any = Field(..., description="Value asserted by this record")
    conflicting_value: Any = Field(..., description="Value asserted by opposing record")
    description: str = Field(..., description="Human-readable explanation of the discrepancy")
    severity: str = Field("medium", description="high, medium, low")
    detected_at: float = Field(default_factory=time.time)


class NormalizedEntities(BaseModel):
    """
    Standardized numerical attributes and canonical entities extracted from text.
    """
    loan_products: List[str] = Field(default_factory=list, description="Standardized product names, e.g. Term Loan")
    entity_types: List[str] = Field(default_factory=list, description="Normalized legal entity types, e.g. LLC, C-Corp")
    time_in_business_months: Optional[int] = Field(None, description="Normalized business age in months")
    time_in_business_display: Optional[str] = Field(None, description="e.g. '24 months (2.0 years)'")
    min_revenue_monthly_usd: Optional[float] = Field(None, description="Normalized minimum monthly gross revenue in USD")
    min_credit_score: Optional[int] = Field(None, description="Normalized minimum credit score")
    min_loan_amount_usd: Optional[float] = Field(None, description="Normalized minimum loan facility amount")
    max_loan_amount_usd: Optional[float] = Field(None, description="Normalized maximum loan facility amount")
    min_apr: Optional[float] = Field(None, description="Minimum APR percentage")
    max_apr: Optional[float] = Field(None, description="Maximum APR percentage")
    repayment_frequency: Optional[str] = Field(None, description="Standardized frequency: Daily, Weekly, Bi-Weekly, Monthly")
    prepayment_penalty_allowed: Optional[bool] = Field(None, description="True if penalty applies, False if zero penalty")
    normalized_dates: List[str] = Field(default_factory=list, description="ISO 8601 formatted dates (YYYY-MM-DD)")


class KnowledgeRecord(BaseModel):
    """
    Standardized Enterprise Knowledge Record.
    Contains clean, redacted, normalized content with full provenance and conflict tracking.
    """
    record_id: str = Field(default_factory=lambda: f"krec_{uuid.uuid4().hex[:10]}")
    source_doc_id: str = Field(..., description="Reference to parent RawDocument.document_id")
    title: str = Field(..., description="Document or section title")
    cleaned_content: str = Field(..., description="Cleaned, redacted, and normalized text")
    original_content_hash: str = Field(..., description="SHA-256 hash of original raw content")
    cleaned_content_hash: str = Field(..., description="SHA-256 hash of cleaned text for deduplication")
    category: str = Field("other", description="product, qualification, policy, faq, objection, marketing, other")
    product: Optional[str] = Field(None, description="Primary loan product name if applicable")
    source: str = Field(..., description="Source file or URL")
    source_location: Dict[str, Any] = Field(default_factory=dict, description="page, section, table_id, row")
    version: Optional[str] = Field("1.0", description="Policy or document version")
    effective_date: Optional[str] = Field(None, description="ISO 8601 effective date")
    normalized_entities: NormalizedEntities = Field(default_factory=NormalizedEntities)
    pii_audit: Dict[str, int] = Field(default_factory=dict, description="Counts of redacted PII items")
    conflicts: List[ConflictRecord] = Field(default_factory=list, description="Contradictions with other records")
    is_duplicate: bool = Field(False, description="True if flagged as exact or near duplicate")
    duplicate_of: Optional[str] = Field(None, description="Record ID this is a duplicate of")
    created_at: float = Field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
