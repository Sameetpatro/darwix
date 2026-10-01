from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    field: str
    issue_type: str  # "conflict", "underwriting_rule", "unrealistic", "missing"
    message: str
    severity: str = "warning"  # "info", "warning", "blocking"


class UnderwritingDecision(BaseModel):
    status: str = "INCOMPLETE"  # "INCOMPLETE", "PRE_QUALIFIED", "NEEDS_REVIEW", "DISQUALIFIED", "ESCALATED"
    is_qualified: bool = False
    reasons: List[str] = Field(default_factory=list)
    suggested_programs: List[str] = Field(default_factory=list)
    max_recommended_amount: Optional[float] = None


class LoanApplication(BaseModel):
    customer_name: Optional[str] = None
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    business_age_months: Optional[int] = None
    business_age_raw: Optional[str] = None
    monthly_revenue: Optional[float] = None
    monthly_revenue_raw: Optional[str] = None
    requested_amount: Optional[float] = None
    requested_amount_raw: Optional[str] = None
    loan_purpose: Optional[str] = None
    has_existing_loans: Optional[bool] = None
    existing_loans_details: Optional[str] = None
    location: Optional[str] = None

    # Qualification & Review Tracking
    is_confirmed: bool = False
    is_escalated: bool = False
    escalation_reason: Optional[str] = None
    active_conflict: Optional[ValidationIssue] = None
    conflict_history: List[ValidationIssue] = Field(default_factory=list)
    handled_objections: List[str] = Field(default_factory=list)

    def get_missing_fields(self) -> List[str]:
        """Returns list of required qualification fields that have not yet been collected."""
        missing = []
        if not self.customer_name:
            missing.append("customer_name")
        if not self.business_name:
            missing.append("business_name")
        if not self.business_type:
            missing.append("business_type")
        if self.business_age_months is None and not self.business_age_raw:
            missing.append("business_age")
        if self.monthly_revenue is None and not self.monthly_revenue_raw:
            missing.append("monthly_revenue")
        if self.requested_amount is None and not self.requested_amount_raw:
            missing.append("requested_amount")
        if not self.loan_purpose:
            missing.append("loan_purpose")
        if self.has_existing_loans is None and not self.existing_loans_details:
            missing.append("existing_loans")
        if not self.location:
            missing.append("location")
        return missing

    def get_collected_count(self) -> int:
        total_slots = 9
        missing = len(self.get_missing_fields())
        return total_slots - missing

    def get_summary_dict(self) -> Dict[str, Any]:
        return {
            "customer_name": self.customer_name,
            "business_name": self.business_name,
            "business_type": self.business_type,
            "business_age": f"{self.business_age_months} months" if self.business_age_months else self.business_age_raw,
            "monthly_revenue": f"${self.monthly_revenue:,.0f}" if self.monthly_revenue else self.monthly_revenue_raw,
            "requested_amount": f"${self.requested_amount:,.0f}" if self.requested_amount else self.requested_amount_raw,
            "loan_purpose": self.loan_purpose,
            "existing_loans": "Yes" if self.has_existing_loans is True else ("No" if self.has_existing_loans is False else self.existing_loans_details),
            "location": self.location,
            "missing_fields": self.get_missing_fields(),
            "collected_count": self.get_collected_count(),
            "total_fields": 9,
            "is_escalated": self.is_escalated,
            "escalation_reason": self.escalation_reason,
        }
