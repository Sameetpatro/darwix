import pytest
from app.qualification.models import LoanApplication
from app.qualification.extractor import extract_qualification_data, parse_dollar_amount, parse_business_age_months
from app.qualification.rules import detect_conflicts, evaluate_qualification
from app.qualification.objections import detect_escalation_intent, detect_objection
from app.qualification.dialog_manager import DialogManager


def test_parse_dollar_amounts():
    assert parse_dollar_amount("$50k") == 50000.0
    assert parse_dollar_amount("100 thousand dollars") == 100000.0
    assert parse_dollar_amount("$1.5 million") == 1500000.0
    assert parse_dollar_amount("25,000") == 25000.0


def test_parse_business_age():
    assert parse_business_age_months("3 years") == 36
    assert parse_business_age_months("18 months") == 18
    assert parse_business_age_months("two years in business") == 24
    assert parse_business_age_months("6 months") == 6


def test_multi_field_extraction():
    utterance = "Hi, my name is David Vance. I own Summit Logistics LLC in Dallas, Texas. We need $80,000 for equipment."
    extracted = extract_qualification_data(utterance)

    assert extracted.get("customer_name") == "David Vance"
    assert "Summit Logistics" in extracted.get("business_name", "")
    assert extracted.get("business_type") == "LLC"
    assert "Dallas" in extracted.get("location", "")
    assert extracted.get("requested_amount") == 80000.0
    assert extracted.get("loan_purpose") == "Equipment"


def test_ask_only_missing_fields():
    app = LoanApplication()
    dm = DialogManager()

    # Turn 1: Caller volunteers name and business name without entity type
    reply1, meta1 = dm.process_turn(app, "My name is Sarah Miller and my business is Apex Horizon.", 1)
    assert app.customer_name == "Sarah Miller"
    assert "Apex Horizon" in (app.business_name or "")
    assert meta1["field"] == "business_type"
    assert "entity" in reply1.lower() or "llc" in reply1.lower()

    # Turn 2: Caller provides entity type
    reply2, meta2 = dm.process_turn(app, "We are registered as an LLC.", 2)
    assert app.business_type == "LLC"
    assert meta2["field"] == "business_age"
    assert "how long" in reply2.lower()


def test_conflict_detection():
    app = LoanApplication(business_age_months=6)

    # Caller later says 5 years (60 months) -> conflict!
    extracted = {"business_age_months": 60}
    conflict = detect_conflicts(app, extracted)

    assert conflict is not None
    assert conflict.field == "business_age"
    assert conflict.issue_type == "conflict"
    assert "discrepancy" in conflict.message or "Earlier you mentioned" in conflict.message


def test_unrealistic_loan_to_revenue_conflict():
    app = LoanApplication(monthly_revenue=2000.0)
    extracted = {"requested_amount": 500000.0}
    conflict = detect_conflicts(app, extracted)

    assert conflict is not None
    assert conflict.issue_type == "unrealistic"
    assert "significantly higher" in conflict.message


def test_underwriting_rules_prequalified():
    app = LoanApplication(
        customer_name="Alice Brown",
        business_name="Green Garden LLC",
        business_type="LLC",
        business_age_months=24,
        monthly_revenue=40000.0,
        requested_amount=60000.0,
        loan_purpose="Working Capital",
        has_existing_loans=False,
        location="Chicago, IL",
        is_confirmed=True,
    )
    decision = evaluate_qualification(app)
    assert decision.status == "PRE_QUALIFIED"
    assert decision.is_qualified is True
    assert len(decision.suggested_programs) > 0


def test_underwriting_rules_disqualified_age():
    app = LoanApplication(
        customer_name="Bob",
        business_name="New Startup",
        business_type="LLC",
        business_age_months=3,  # < 6 months
        monthly_revenue=20000.0,
        requested_amount=30000.0,
        loan_purpose="Inventory",
        has_existing_loans=False,
        location="Austin, TX",
        is_confirmed=True,
    )
    decision = evaluate_qualification(app)
    assert decision.status == "DISQUALIFIED"
    assert decision.is_qualified is False
    assert "minimum of 6 months" in decision.reasons[0]


def test_underwriting_rules_needs_review_high_ratio():
    app = LoanApplication(
        customer_name="Charlie",
        business_name="Charlie Freight",
        business_type="LLC",
        business_age_months=24,
        monthly_revenue=15000.0,
        requested_amount=80000.0,  # 80k / 15k = 5.3x monthly revenue (> 3.5x)
        loan_purpose="Expansion",
        has_existing_loans=False,
        location="Denver, CO",
        is_confirmed=True,
    )
    decision = evaluate_qualification(app)
    assert decision.status == "NEEDS_REVIEW"
    assert decision.is_qualified is True
    assert "senior underwriter" in decision.reasons[0]


def test_objection_handling():
    category, reply = detect_objection("What are your interest rates? Are they high?")
    assert category == "interest_rate"
    assert "APR" in reply or "competitive rate" in reply

    cat2, rep2 = detect_objection("Will this check hurt my credit score?")
    assert cat2 == "credit_check"
    assert "soft credit" in rep2


def test_human_escalation_intent():
    is_esc, reason = detect_escalation_intent("I want to speak with a human representative please.")
    assert is_esc is True
    assert reason == "customer_requested_human"

    is_esc2, _ = detect_escalation_intent("Can you transfer me to a real person?")
    assert is_esc2 is True

    is_esc3, _ = detect_escalation_intent("We sell retail clothing in Ohio.")
    assert is_esc3 is False
