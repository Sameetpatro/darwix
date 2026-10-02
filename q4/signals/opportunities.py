import time
import re
from typing import Optional
from q4.conversation.buffer import ConversationTurn
from q4.conversation.state import LiveCallState
from q4.signals.models import ConversationSignal, SignalType, SignalSeverity
from q4.jev.laya_signal_classifier import laya_signal_classifier


class OpportunityDetector:
    """
    Detects revenue expansion and cross-sell opportunities in real time.
    Required example: Customer mentions another vehicle -> cross_sell_opportunity.
    Must filter out 3rd-party mentions (e.g., 'My brother has another vehicle') and
    ambiguous fragments ('I... uh... maybe... another...').
    """

    def __init__(self):
        self.signal_type = SignalType.CROSS_SELL_OPPORTUNITY

    def detect(self, turn: ConversationTurn, state: LiveCallState) -> Optional[ConversationSignal]:
        # Only customer utterances can represent direct cross-sell intent
        if turn.speaker != "customer":
            return None

        text = turn.text.strip()
        lowered = text.lower()

        # Quick candidate filter: mentions of vehicles, cars, policies, properties
        candidate_keywords = ["car", "vehicle", "truck", "suv", "motorcycle", "auto", "policy", "van", "house", "coverage"]
        if not any(k in lowered for k in candidate_keywords):
            return None

        # Jev/Laya semantic confidence & ownership verification
        conf, reason = laya_signal_classifier.evaluate_signal_confidence(
            signal_type=self.signal_type.value,
            text=text,
            speaker=turn.speaker
        )

        # Build structured signal
        topic = "vehicle_insurance" if any(v in lowered for v in ["car", "vehicle", "truck", "suv", "motorcycle", "auto"]) else "cross_sell"

        signal = ConversationSignal(
            call_id=state.call_id,
            timestamp=round(time.time(), 2),
            type=self.signal_type.value,
            speaker=turn.speaker,
            confidence=conf,
            evidence=text,
            topic=topic,
            severity=SignalSeverity.MEDIUM.value,
            status="new",
            metadata={
                "classifier": "laya_system_one",
                "reason": reason,
                "turn_id": turn.turn_id
            }
        )

        return signal


opportunity_detector = OpportunityDetector()
