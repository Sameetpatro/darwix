from typing import Optional, List, Dict, Any, Tuple
from app.qualification.models import LoanApplication, ValidationIssue, UnderwritingDecision

MIN_MONTHS_IN_BUSINESS = 6
RECOMMENDED_MONTHS_IN_BUSINESS = 12
MIN_MONTHLY_REVENUE = 10000.0  # $10,000/mo
MAX_UNSECURED_LOAN_TO_REVENUE_RATIO = 3.5  # Max 3.5x monthly revenue for unsecured loans


def detect_conflicts(app: LoanApplication, incoming: Dict[str, Any]) -> Optional[ValidationIssue]:
    """
    Detects if newly provided information directly conflicts with existing recorded information.
    """
    # 1. Business Age Conflict
    new_age = incoming.get("business_age_months")
    if new_age is not None and app.business_age_months is not None:
        diff_months = abs(new_age - app.business_age_months)
        if diff_months >= 12:  # Over a year difference
            return ValidationIssue(
                field="business_age",
                issue_type="conflict",
                message=f"Earlier you mentioned your business has been open for {app.business_age_months} months, but you just noted {new_age} months.",
                severity="warning",
            )

    # 2. Monthly Revenue Conflict
    new_rev = incoming.get("monthly_revenue")
    if new_rev is not None and app.monthly_revenue is not None:
        if abs(new_rev - app.monthly_revenue) / max(app.monthly_revenue, 1) > 0.6:  # > 60% discrepancy
            return ValidationIssue(
                field="monthly_revenue",
                issue_type="conflict",
                message=f"Earlier we noted monthly revenue around ${app.monthly_revenue:,.0f}, but you just mentioned ${new_rev:,.0f}.",
                severity="warning",
            )

    # 3. Requested Amount Conflict
    new_req = incoming.get("requested_amount")
    if new_req is not None and app.requested_amount is not None:
        if abs(new_req - app.requested_amount) / max(app.requested_amount, 1) > 0.75:
            return ValidationIssue(
                field="requested_amount",
                issue_type="conflict",
                message=f"Earlier you requested ${app.requested_amount:,.0f}, but you just mentioned ${new_req:,.0f}.",
                severity="warning",
            )

    # 4. Disproportionate Revenue vs Loan Request (Financial Inconsistency)
    target_rev = new_rev or app.monthly_revenue
    target_req = new_req or app.requested_amount
    if target_rev and target_req and target_rev > 0:
        ratio = target_req / target_rev
        if ratio > 15.0 and target_req >= 100000:
            return ValidationIssue(
                field="requested_amount",
                issue_type="unrealistic",
                message=f"A requested loan of ${target_req:,.0f} is significantly higher than monthly revenue of ${target_rev:,.0f} (over {ratio:.0f}x monthly revenue).",
                severity="warning",
            )

    return None


def evaluate_qualification(app: LoanApplication) -> UnderwritingDecision:
    """
    Applies standard commercial business-loan qualification rules.
    """
    if app.is_escalated:
        return UnderwritingDecision(
            status="ESCALATED",
            is_qualified=False,
            reasons=[app.escalation_reason or "Escalated to human lending specialist."],
        )

    missing = app.get_missing_fields()
    if missing:
        return UnderwritingDecision(
            status="INCOMPLETE",
            is_qualified=False,
            reasons=[f"Missing required fields: {', '.join(missing)}"],
        )

    reasons = []
    suggested_programs = []
    max_amount = None

    # Check Business Age Rule
    age = app.business_age_months or 0
    if age < MIN_MONTHS_IN_BUSINESS:
        return UnderwritingDecision(
            status="DISQUALIFIED",
            is_qualified=False,
            reasons=[
                f"Business age is {age} months. Standard commercial term loans require a minimum of {MIN_MONTHS_IN_BUSINESS} months in operations."
            ],
            suggested_programs=["Personal Guarantee Startup Credit Lines", "Equipment Leasing"],
        )
    elif age < RECOMMENDED_MONTHS_IN_BUSINESS:
        reasons.append("Less than 12 months in business: eligible for bridge or short-term working capital.")
        suggested_programs.append("Short-term Working Capital")
    else:
        suggested_programs.append("Prime Commercial Term Loan")
        suggested_programs.append("Revolving Business Line of Credit")

    # Check Monthly Revenue Rule
    rev = app.monthly_revenue or 0.0
    if rev < MIN_MONTHLY_REVENUE:
        return UnderwritingDecision(
            status="DISQUALIFIED",
            is_qualified=False,
            reasons=[
                f"Monthly revenue (${rev:,.0f}) is below our program minimum of ${MIN_MONTHLY_REVENUE:,.0f}/month ($120,000/year)."
            ],
            suggested_programs=["SBA Community Advantage Microloans"],
        )

    # Check Requested Amount vs Revenue Ratio
    req = app.requested_amount or 0.0
    max_amount = round(rev * 2.5, -3)  # Standard guideline: ~2.5x monthly revenue
    ratio = req / rev if rev > 0 else 999.0

    if ratio > MAX_UNSECURED_LOAN_TO_REVENUE_RATIO:
        return UnderwritingDecision(
            status="NEEDS_REVIEW",
            is_qualified=True,
            reasons=[
                f"Requested amount (${req:,.0f}) exceeds standard unsecured ratio ({ratio:.1f}x monthly revenue). A senior underwriter will evaluate collateral or SBA enhancement options."
            ],
            suggested_programs=["SBA 7(a) Loan", "Asset-Backed Commercial Loan"],
            max_recommended_amount=max_amount,
        )

    # Existing loans review
    if app.has_existing_loans:
        reasons.append("Existing commercial debt noted: subject to debt service coverage ratio (DSCR >= 1.25x).")
        suggested_programs.append("Debt Refinance / Consolidation")

    reasons.append(f"Business age ({age} months) and monthly revenue (${rev:,.0f}) meet prime underwriting guidelines.")

    return UnderwritingDecision(
        status="PRE_QUALIFIED",
        is_qualified=True,
        reasons=reasons,
        suggested_programs=suggested_programs,
        max_recommended_amount=max_amount,
    )
