import time
from typing import Optional
from q4.conversation.buffer import ConversationTurn
from q4.conversation.state import LiveCallState
from q4.signals.models import ConversationSignal, SignalType, SignalSeverity
from q4.jev.laya_signal_classifier import laya_signal_classifier


class SentimentDetector:
    """
    Detects customer frustration, repetition complaints, and conversational tension in real time.
    Required example:
    Customer: 'I already told you this three times.' or 'I've already explained this twice.'
    Result -> frustration signal (confidence: >= 0.87, severity: high)
    """

    def __init__(self):
        self.signal_type = SignalType.FRUSTRATION

    def detect(self, turn: ConversationTurn, state: LiveCallState) -> Optional[ConversationSignal]:
        # Only evaluate customer utterances for customer frustration
        if turn.speaker != "customer":
            return None

        text = turn.text.strip()
        lowered = text.lower()

        # Frustration candidate markers
        frustration_triggers = [
            "already told you", "already explained", "told you twice", "told you three times",
            "explained this twice", "asking again", "asked again", "third time",
            "ridiculous", "frustrated", "terrible service", "waste of time",
            "unacceptable", "how many times", "stop asking", "annoyed",
            "don't understand why you"
        ]

        if not any(trigger in lowered for trigger in frustration_triggers):
            return None

        # Score confidence using Jev/Laya System 1 evaluation
        conf, reason = laya_signal_classifier.evaluate_signal_confidence(
            signal_type=self.signal_type.value,
            text=text,
            speaker=turn.speaker
        )

        signal = ConversationSignal(
            call_id=state.call_id,
            timestamp=round(time.time(), 2),
            type=self.signal_type.value,
            speaker=turn.speaker,
            confidence=conf,
            evidence=text,
            topic="customer_satisfaction",
            severity=SignalSeverity.HIGH.value,
            status="new",
            metadata={
                "classifier": "laya_system_one",
                "reason": reason,
                "turn_id": turn.turn_id
            }
        )

        return signal


sentiment_detector = SentimentDetector()
