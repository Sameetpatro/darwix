import time
from typing import Optional, List
from q4.conversation.buffer import ConversationTurn
from q4.conversation.state import LiveCallState
from q4.signals.models import ConversationSignal, SignalType, SignalSeverity


class ComplianceDetector:
    """
    Deterministic compliance and regulatory rule auditor.
    Detects compliance gaps in real time without expensive LLM polling.
    Example:
    Customer: 'Okay, let's continue.'
    Agent: [Does not provide required disclosure]
    Result -> compliance_gap (confidence: 0.96, severity: high)
    """

    MANDATORY_DISCLOSURES = {
        "mandatory_disclosure": "California Insurance & Cancellation Rights Disclosure"
    }

    def __init__(self):
        self.signal_type = SignalType.COMPLIANCE_GAP

    def detect(self, turn: ConversationTurn, state: LiveCallState) -> Optional[ConversationSignal]:
        text_lower = turn.text.lower()

        # If agent speaks the required disclosure, mark it as fulfilled
        if turn.speaker == "agent":
            if any(term in text_lower for term in [
                "disclosure", "terms and conditions", "california insurance disclosure",
                "call is recorded", "policy cancellation rights", "licensed agent disclosure"
            ]):
                state.disclosures_given.add("mandatory_disclosure")
                return None

        # Check for trigger conditions from customer pushing forward into binding/policy agreement
        proceed_triggers = [
            "let's continue", "lets continue", "continue", "sign me up",
            "go ahead", "finalize the policy", "ready to buy", "proceed",
            "take my payment", "bind the policy"
        ]

        customer_advancing = (turn.speaker == "customer" and any(p in text_lower for p in proceed_triggers))
        stage_advancing = state.stage in ["binding_ready", "binding", "closing"]

        if customer_advancing or stage_advancing:
            # Check if mandatory disclosure is missing
            if "mandatory_disclosure" not in state.disclosures_given:
                evidence = turn.text if customer_advancing else f"Call reached '{state.stage}' stage without mandatory disclosure"
                return ConversationSignal(
                    call_id=state.call_id,
                    timestamp=round(time.time(), 2),
                    type=self.signal_type.value,
                    speaker="system" if not customer_advancing else "customer",
                    confidence=0.96,
                    evidence=evidence,
                    topic="compliance",
                    severity=SignalSeverity.HIGH.value,
                    status="new",
                    metadata={
                        "rule": "MANDATORY_STAGE_DISCLOSURE",
                        "missing_disclosure": "mandatory_disclosure",
                        "stage": state.stage,
                        "turn_id": turn.turn_id
                    }
                )

        return None


compliance_detector = ComplianceDetector()
