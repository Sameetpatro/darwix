import pytest
from app.qualification.models import LoanApplication
from app.qualification.dialog_manager import DialogManager
from app.kb.retriever import STRICT_FALLBACK_TEXT


def test_scenario_1_cooperative_customer():
    """
    Scenario 1: Cooperative Customer
    Caller provides clean answers to qualification questions, confirms details,
    and receives a PRE_QUALIFIED underwriting decision.
    """
    dm = DialogManager()
    app = LoanApplication()

    # Turn 1: Name and Business Name
    t1_reply, t1_meta = dm.process_turn(app, "My name is John Smith and my company is Smith Logistics LLC.", 1)
    assert app.customer_name == "John Smith"
    assert app.business_name == "Smith Logistics LLC"
    assert "business_age" in t1_meta["missing_fields"]

    # Turn 2: Business Age and Revenue
    t2_reply, t2_meta = dm.process_turn(app, "We have been operating for 4 years and do about $50,000 in monthly revenue.", 2)
    assert app.business_age_months == 48
    assert app.monthly_revenue == 50000.0

    # Turn 3: Requested Amount and Purpose
    t3_reply, t3_meta = dm.process_turn(app, "Looking for $100,000 for fleet expansion and new trucks.", 3)
    assert app.requested_amount == 100000.0
    assert any(p in (app.loan_purpose or "").lower() for p in ["expansion", "equipment", "fleet"])

    # Turn 4: Existing Loans and Location
    t4_reply, t4_meta = dm.process_turn(app, "We have no existing debt loans, and we are based in Dallas, Texas.", 4)
    assert app.has_existing_loans is False
    assert "Dallas, TX" in (app.location or "")

    # Turn 5: Confirm details
    assert t4_meta["action"] == "confirm_details"
    t5_reply, t5_meta = dm.process_turn(app, "Yes, that is completely correct.", 5)

    # Decision
    assert t5_meta["action"] == "underwriting_decision"
    decision = t5_meta["decision"]
    assert decision["status"] == "PRE_QUALIFIED"
    assert "Smith Logistics" in t4_reply or "John Smith" in t4_reply


def test_scenario_2_objection_handling():
    """
    Scenario 2: Objection Handling
    Caller expresses fear of high interest rates and broker fees.
    Agent provides grounded reassurance and continues qualification.
    """
    dm = DialogManager()
    app = LoanApplication()

    reply, meta = dm.process_turn(
        app,
        "I'm hesitant because I am worried your interest rates are too high and brokers charge hidden fees.",
        1
    )
    # Rebuttal from objection guide or FAQ
    lowered = reply.lower()
    assert "competitive" in lowered or "rates" in lowered or "upfront" in lowered or "soft" in lowered
    # Verifies agent still asks for qualification info
    assert meta["action"] in ["ask_field", "kb_and_ask_field"]


def test_scenario_3_incomplete_information():
    """
    Scenario 3: Incomplete Information
    Caller provides vague single-phrase answers; agent methodically prompts only
    for the missing fields without skipping.
    """
    dm = DialogManager()
    app = LoanApplication()

    # Only gives name
    t1_reply, t1_meta = dm.process_turn(app, "I'm David Lee.", 1)
    assert app.customer_name == "David Lee"
    assert "business_name" in t1_meta["missing_fields"]
    assert "business" in t1_reply.lower()

    # Only gives business name
    t2_reply, t2_meta = dm.process_turn(app, "Lee Bakery.", 2)
    assert app.business_name == "Lee Bakery"
    assert "business_age" in t2_meta["missing_fields"] or "business_type" in t2_meta["missing_fields"]

    # Incomplete slots tracked accurately
    assert app.get_collected_count() >= 2
    assert len(app.get_missing_fields()) > 0


def test_scenario_4_conflicting_information():
    """
    Scenario 4: Conflicting Information
    Caller states $8,000/mo monthly revenue, but requests $2,000,000 unsecured loan
    (250x revenue leverage ratio exceeding the maximum 4x rule).
    Agent flags conflict and prompts for clarification.
    """
    dm = DialogManager()
    app = LoanApplication()
    app.customer_name = "Marcus Vance"
    app.business_name = "Vance Holdings"
    app.business_type = "LLC"
    app.business_age_months = 36
    app.monthly_revenue = 8000.0

    # User requests $2,000,000 loan which creates an extreme ratio conflict
    reply, meta = dm.process_turn(app, "We want to borrow $2,000,000 for general capital.", 2)
    assert meta["action"] == "resolve_conflict"
    assert "discrepancy" in reply.lower() or "ratio" in reply.lower() or "clarify" in reply.lower()
    assert app.active_conflict is not None
    assert app.active_conflict.field in ["requested_amount", "monthly_revenue"]


def test_scenario_5_out_of_scope_question():
    """
    Scenario 5: Out-of-Scope Question
    Caller asks about trading crypto/Bitcoin with the loan.
    Agent strictly delivers the non-hallucination fallback.
    """
    dm = DialogManager()
    app = LoanApplication()

    reply, meta = dm.process_turn(app, "Can I use this loan to trade crypto tokens and Bitcoin futures?", 1)
    assert meta["action"] == "kb_fallback"
    assert reply == STRICT_FALLBACK_TEXT
    assert meta.get("citation") is None


def test_scenario_6_human_assistance_request():
    """
    Scenario 6: Human Assistance Request
    Caller requests a human representative or manager.
    Agent immediately triggers escalation.
    """
    dm = DialogManager()
    app = LoanApplication()

    reply, meta = dm.process_turn(app, "I'd like to speak with a human agent or manager please.", 1)
    assert meta["action"] == "escalate"
    assert app.is_escalated is True
    assert "transfer you" in reply.lower() or "senior lending advisor" in reply.lower()
