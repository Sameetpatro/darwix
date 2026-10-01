from typing import Tuple, Optional, Dict, Any, List
import re
from app.qualification.models import LoanApplication, ValidationIssue, UnderwritingDecision
from app.qualification.extractor import extract_qualification_data
from app.qualification.rules import detect_conflicts, evaluate_qualification
from app.qualification.objections import detect_escalation_intent, detect_objection
from app.kb.retriever import retriever, STRICT_FALLBACK_TEXT
from app.logging_config import logger

QUESTIONS = {
    "customer_name": "Could you please tell me your name and your business name?",
    "business_name": "What is the name of your business?",
    "business_type": "What type of business entity do you operate, such as an LLC or Corporation?",
    "business_age": "How long has your business been in operation?",
    "monthly_revenue": "Approximately what is your average gross monthly revenue?",
    "requested_amount": "How much financing are you looking to secure today?",
    "loan_purpose": "What is the primary purpose for the loan, such as working capital, equipment, or expansion?",
    "existing_loans": "Do you currently carry any existing commercial business loans or debt balances?",
    "location": "What city and state is your business located in?",
}


def is_inquiry_or_question(text: str) -> bool:
    """Detects if the caller is asking an informational question."""
    lowered = text.lower().strip()
    if "?" in text:
        return True
    inquiry_prefixes = [
        "what", "how", "can i", "can we", "do you", "do we", "is there", "are there",
        "tell me about", "explain", "will this", "does this", "where can", "why do",
        "who is", "could you explain", "what about", "is it possible"
    ]
    return any(lowered.startswith(p) or f" {p} " in lowered for p in inquiry_prefixes)


class DialogManager:
    def process_turn(
        self,
        app: LoanApplication,
        user_utterance: str,
        turn_number: int,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Coordinates the qualification dialogue with Knowledge Base retrieval:
        1. Checks for human escalation.
        2. Checks for knowledge base inquiries / out-of-scope questions.
        3. Checks for customer objections.
        4. Extracts qualification slots.
        5. Detects and clarifies conflicting information.
        6. Confirms important information.
        7. Asks only for remaining missing fields.
        8. Delivers underwriting decision once complete.
        """
        user_text = user_utterance.strip()
        lowered = user_text.lower()
        missing = app.get_missing_fields()

        # Step 1: Detect Human Escalation Request
        is_escalate, reason = detect_escalation_intent(user_text)
        if is_escalate:
            app.is_escalated = True
            app.escalation_reason = reason or "Customer requested human representative."
            logger.info("[QUALIFICATION] Escalating call to human specialist: %s", reason)
            return (
                "I completely understand. Let me transfer you directly to one of our senior lending advisors who can assist you immediately. Please hold for just a moment.",
                {"action": "escalate", "status": "ESCALATED", "app_summary": app.get_summary_dict()},
            )

        # Step 2: Knowledge Base RAG Inquiry Check
        kb_prefix = ""
        kb_citation = None
        if is_inquiry_or_question(user_text):
            kb_res = retriever.query_with_fallback(user_text)

            # Strict Fallback Check: If information is NOT in KB, never hallucinate
            if not kb_res.has_match:
                logger.info("[QUALIFICATION] Question out-of-scope or missing from KB. Returning strict fallback.")
                return (
                    STRICT_FALLBACK_TEXT,
                    {
                        "action": "kb_fallback",
                        "citation": None,
                        "confidence": kb_res.confidence_score,
                        "app_summary": app.get_summary_dict(),
                    },
                )
            else:
                kb_prefix = f"{kb_res.voice_answer} "
                kb_citation = kb_res.citation

        # Step 3: Detect Objections
        objection = detect_objection(user_text)
        objection_prefix = ""
        if objection and not kb_prefix:
            cat, reply = objection
            if cat not in app.handled_objections:
                app.handled_objections.append(cat)
                objection_prefix = f"{reply} "
                logger.info("[QUALIFICATION] Handled objection '%s'", cat)

        # Step 3: Extract Data
        extracted = extract_qualification_data(user_text, current_missing=missing)

        # Step 4: Check For Information Conflicts
        conflict = detect_conflicts(app, extracted)
        if conflict:
            app.active_conflict = conflict
            app.conflict_history.append(conflict)
            logger.warning("[QUALIFICATION] Conflict detected: %s", conflict.message)
            return (
                f"{objection_prefix}I noticed a slight discrepancy: {conflict.message} Could you please clarify which number is accurate for your records?",
                {"action": "resolve_conflict", "issue": conflict.model_dump(), "app_summary": app.get_summary_dict()},
            )
        else:
            app.active_conflict = None

        # Step 5: Update Application with Extracted Data
        if "customer_name" in extracted and not app.customer_name:
            app.customer_name = extracted["customer_name"]
        if "business_name" in extracted and not app.business_name:
            app.business_name = extracted["business_name"]
        if "business_type" in extracted and not app.business_type:
            app.business_type = extracted["business_type"]
        if "business_age_months" in extracted:
            app.business_age_months = extracted["business_age_months"]
            app.business_age_raw = extracted.get("business_age_raw")
        if "monthly_revenue" in extracted:
            app.monthly_revenue = extracted["monthly_revenue"]
            app.monthly_revenue_raw = extracted.get("monthly_revenue_raw")
        if "requested_amount" in extracted:
            app.requested_amount = extracted["requested_amount"]
            app.requested_amount_raw = extracted.get("requested_amount_raw")
        if "loan_purpose" in extracted and not app.loan_purpose:
            app.loan_purpose = extracted["loan_purpose"]
        if "has_existing_loans" in extracted:
            app.has_existing_loans = extracted["has_existing_loans"]
            app.existing_loans_details = extracted.get("existing_loans_details")
        if "location" in extracted and not app.location:
            app.location = extracted["location"]

        updated_missing = app.get_missing_fields()

        # Step 6: Confirmation of critical info if almost complete or user confirms
        if not updated_missing and not app.is_confirmed:
            if any(w in lowered for w in ["yes", "correct", "right", "exactly", "that is right", "yep"]):
                app.is_confirmed = True
            else:
                # Deliver explicit confirmation before final underwriting
                confirmation_msg = (
                    f"{objection_prefix}Thank you, {app.customer_name or 'there'}. "
                    f"Just to confirm all details: you are requesting ${app.requested_amount:,.0f} for {app.business_name or 'your business'}, "
                    f"generating about ${app.monthly_revenue:,.0f} monthly for {app.loan_purpose or 'business needs'}. Does that all sound accurate?"
                )
                return confirmation_msg, {"action": "confirm_details", "app_summary": app.get_summary_dict()}

        # Step 7: All fields collected and confirmed -> Underwriting Decision
        if not updated_missing and app.is_confirmed:
            decision: UnderwritingDecision = evaluate_qualification(app)
            logger.info("[QUALIFICATION] Underwriting Decision: %s", decision.status)

            if decision.status == "PRE_QUALIFIED":
                reply = (
                    f"Excellent news! Based on your {app.business_age_months or 12} months in business and monthly revenue of ${app.monthly_revenue:,.0f}, "
                    f"your business pre-qualifies for our {decision.suggested_programs[0] if decision.suggested_programs else 'Commercial Term Loan'}. "
                    f"I will prepare your preliminary approval paperwork right away."
                )
            elif decision.status == "NEEDS_REVIEW":
                reply = (
                    f"Thank you for confirming. Because your requested amount of ${app.requested_amount:,.0f} is high relative to monthly revenue, "
                    f"your application has been routed to our senior underwriting desk for customized structuring. We will follow up with next steps."
                )
            elif decision.status == "DISQUALIFIED":
                reply = (
                    f"Thank you for sharing your details. Our standard commercial program requires a minimum of {decision.reasons[0]}. "
                    f"However, we can look into our alternative microloan or equipment leasing programs. Would you like me to transfer you to a specialist?"
                )
            else:
                reply = "Thank you. Your business loan application details have been recorded successfully."

            return reply, {"action": "underwriting_decision", "decision": decision.model_dump(), "app_summary": app.get_summary_dict()}

        # Step 8: Ask ONLY for the next missing information
        next_field = updated_missing[0]
        next_question = QUESTIONS.get(next_field, "Could you provide more details about your loan request?")

        # Natural transition phrases
        acknowledgments = {
            "business_type": "Got it. ",
            "business_age": "Understood. ",
            "monthly_revenue": "Thank you. ",
            "requested_amount": "Great. ",
            "loan_purpose": "Noted. ",
            "existing_loans": "Understood. ",
            "location": "Almost done. ",
        }
        ack = acknowledgments.get(next_field, "")
        final_reply = f"{kb_prefix}{objection_prefix}{ack}{next_question}".strip()

        return final_reply, {
            "action": "kb_and_ask_field" if kb_citation else "ask_field",
            "field": next_field,
            "missing_fields": updated_missing,
            "collected_count": app.get_collected_count(),
            "app_summary": app.get_summary_dict(),
            "kb_citation": kb_citation,
        }


dialog_manager = DialogManager()
