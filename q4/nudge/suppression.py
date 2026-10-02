import time
from typing import Set, Dict, Optional
from q4.signals.models import ConversationSignal, SignalType
from q4.conversation.state import LiveCallState
from q4.nudge.cooldown import cooldown_manager, CooldownManager
from q4.nudge.models import SuppressionCheckResult


class SuppressionEngine:
    """
    Evaluates in-flight signals against suppression rules to prevent agent notification fatigue:
      1. Confidence Threshold (e.g. < 0.75 -> suppress)
      2. Duplicate Suppression (identical signal/evidence already alerted)
      3. Cooldown Check (20-second cooldown per signal type)
      4. Contextual Expiration (agent already addressed or disclosure already fulfilled)
    """

    def __init__(
        self,
        min_confidence_threshold: float = 0.75,
        cooldown_seconds: float = 20.0,
        cooldown_mgr: Optional[CooldownManager] = None
    ):
        self.min_confidence_threshold = min_confidence_threshold
        self.cooldown_seconds = cooldown_seconds
        self.cooldown_mgr = cooldown_mgr or cooldown_manager
        
        # Track active/shown signal evidence hashes per call
        # Key: (call_id, signal_type, evidence_normalized)
        self._shown_signals: Set[str] = set()

    def evaluate(self, signal: ConversationSignal, state: LiveCallState) -> SuppressionCheckResult:
        """
        Runs comprehensive suppression pipeline.
        Returns SuppressionCheckResult indicating if a nudge should be generated.
        """
        # 1. Confidence Threshold Rule
        if signal.confidence < self.min_confidence_threshold:
            return SuppressionCheckResult(
                should_nudge=False,
                suppressed=True,
                rule="CONFIDENCE_THRESHOLD",
                reason=f"Confidence {signal.confidence:.2f} is below threshold {self.min_confidence_threshold:.2f}"
            )

        # 2. Contextual Resolution Rule (Has the agent already resolved this?)
        if signal.type == SignalType.COMPLIANCE_GAP.value:
            if "mandatory_disclosure" in state.disclosures_given:
                return SuppressionCheckResult(
                    should_nudge=False,
                    suppressed=True,
                    rule="ALREADY_RESOLVED",
                    reason="Mandatory disclosure was already spoken by the agent"
                )

        if signal.type == SignalType.CROSS_SELL_OPPORTUNITY.value:
            if "multi_vehicle_offered" in state.disclosures_given:
                return SuppressionCheckResult(
                    should_nudge=False,
                    suppressed=True,
                    rule="ALREADY_RESOLVED",
                    reason="Multi-vehicle coverage was already offered by agent"
                )

        # 3. Duplicate Evidence Check
        norm_evidence = signal.evidence.strip().lower()
        signal_fingerprint = f"{signal.call_id}:{signal.type}:{norm_evidence}"
        if signal_fingerprint in self._shown_signals:
            return SuppressionCheckResult(
                should_nudge=False,
                suppressed=True,
                rule="DUPLICATE_SUPPRESSION",
                reason="Identical signal utterance already generated an active nudge"
            )

        # 4. Cooldown Check (20 seconds default)
        is_cooling, remaining = self.cooldown_mgr.is_on_cooldown(
            call_id=signal.call_id,
            signal_type=signal.type,
            topic=signal.topic,
            cooldown_seconds=self.cooldown_seconds
        )
        if is_cooling:
            return SuppressionCheckResult(
                should_nudge=False,
                suppressed=True,
                rule="COOLDOWN_ACTIVE",
                reason=f"Signal type '{signal.type}' is on cooldown ({remaining}s remaining)"
            )

        # All suppression checks passed
        return SuppressionCheckResult(
            should_nudge=True,
            suppressed=False,
            reason="Signal passed all suppression filters"
        )

    def mark_shown(self, signal: ConversationSignal):
        """Registers signal as shown in duplicate tracking and initiates cooldown."""
        norm_evidence = signal.evidence.strip().lower()
        signal_fingerprint = f"{signal.call_id}:{signal.type}:{norm_evidence}"
        self._shown_signals.add(signal_fingerprint)
        
        self.cooldown_mgr.record_nudge(
            call_id=signal.call_id,
            signal_type=signal.type,
            topic=signal.topic
        )

    def reset_call(self, call_id: str):
        """Cleans up call records upon termination."""
        prefix = f"{call_id}:"
        self._shown_signals = {s for s in self._shown_signals if not s.startswith(prefix)}
        self.cooldown_mgr.reset_call(call_id)


suppression_engine = SuppressionEngine()
