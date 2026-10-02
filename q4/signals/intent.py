import time
from typing import Optional
from q4.conversation.buffer import ConversationTurn
from q4.conversation.state import LiveCallState
from q4.signals.models import ConversationSignal, SignalType, SignalSeverity
from q4.jev.laya_signal_classifier import laya_signal_classifier


class IntentDetector:
    """
    Detects customer payment difficulty, financial distress, and core intent signals in real time.
    Required example:
    Customer: "I don't think I can make the payment this month."
    Result -> payment_difficulty (confidence: 0.93, severity: high)
    """

    def __init__(self):
        pass

    def detect(self, turn: ConversationTurn, state: LiveCallState) -> Optional[ConversationSignal]:
        if turn.speaker != "customer":
            return None

        text = turn.text.strip()
        lowered = text.lower()

        # Check for payment difficulty triggers
        payment_triggers = [
            "can't make the payment", "cannot make the payment", "don't think i can make the payment",
            "cant make the payment", "struggling to pay", "hard to pay", "afford this month",
            "tight on cash", "lost my job", "need an extension", "skip a payment",
            "cannot afford", "unable to pay", "struggling financially"
        ]

        if any(trigger in lowered for trigger in payment_triggers):
            conf, reason = laya_signal_classifier.evaluate_signal_confidence(
                signal_type=SignalType.PAYMENT_DIFFICULTY.value,
                text=text,
                speaker=turn.speaker
            )

            return ConversationSignal(
                call_id=state.call_id,
                timestamp=round(time.time(), 2),
                type=SignalType.PAYMENT_DIFFICULTY.value,
                speaker=turn.speaker,
                confidence=conf,
                evidence=text,
                topic="billing_and_payments",
                severity=SignalSeverity.HIGH.value,
                status="new",
                metadata={
                    "classifier": "laya_system_one",
                    "reason": reason,
                    "turn_id": turn.turn_id
                }
            )

        return None


intent_detector = IntentDetector()
