import time
from typing import Optional, List, Dict, Any
from app.logging_config import logger
from q4.signals.models import ConversationSignal
from q4.conversation.state import LiveCallState
from q4.nudge.models import NudgeEvent, SuppressionCheckResult
from q4.nudge.suppression import suppression_engine, SuppressionEngine
from q4.nudge.generator import nudge_generator, NudgeGenerator


class NudgeEngine:
    """
    Coordinates suppression checks, priority mapping, and nudge generation.
    Enforces that:
      Signal -> Confidence check -> Duplicate check -> Cooldown check -> Priority -> Nudge
    Measures Latency L3 (Signal Detection -> Nudge Generation).
    """

    def __init__(
        self,
        suppression_eng: Optional[SuppressionEngine] = None,
        generator: Optional[NudgeGenerator] = None
    ):
        self.suppression_engine = suppression_eng or suppression_engine
        self.generator = generator or nudge_generator
        
        # In-memory tracking
        self.active_nudges: List[NudgeEvent] = []
        self.suppressed_signals: List[Dict[str, Any]] = []
        self.latencies_l3: List[float] = []

    async def process_signal(
        self,
        signal: ConversationSignal,
        state: LiveCallState,
        use_deepseek: bool = False
    ) -> Optional[NudgeEvent]:
        """
        Processes a conversation signal through suppression rules.
        If approved, generates a NudgeEvent and starts cooldown.
        """
        # 1. Run suppression pipeline
        supp_result = self.suppression_engine.evaluate(signal, state)
        if not supp_result.should_nudge:
            logger.info(
                "[NUDGE_SUPPRESSED] Signal '%s' suppressed by rule %s: %s",
                signal.type, supp_result.rule, supp_result.reason
            )
            self.suppressed_signals.append({
                "signal_id": signal.signal_id,
                "type": signal.type,
                "confidence": signal.confidence,
                "rule": supp_result.rule,
                "reason": supp_result.reason,
                "timestamp": time.time()
            })
            return None

        # 2. Passed suppression: Generate concise nudge
        t0 = time.perf_counter()
        nudge = await self.generator.generate_nudge(signal, state, use_deepseek=use_deepseek)
        l3_ms = round((time.perf_counter() - t0) * 1000, 2)
        self.latencies_l3.append(l3_ms)

        # 3. Mark shown in suppression engine (registers duplicate and cooldown timer)
        self.suppression_engine.mark_shown(signal)
        self.active_nudges.append(nudge)

        return nudge

    def get_suppression_stats(self) -> Dict[str, Any]:
        """Returns statistics on suppression rules fired."""
        rules_count: Dict[str, int] = {}
        for item in self.suppressed_signals:
            r = item.get("rule", "OTHER")
            rules_count[r] = rules_count.get(r, 0) + 1

        return {
            "total_nudges_generated": len(self.active_nudges),
            "total_signals_suppressed": len(self.suppressed_signals),
            "suppression_breakdown": rules_count
        }

    def get_latency_stats(self) -> Dict[str, float]:
        """Calculates percentile distribution for L3 nudge generation latency."""
        if not self.latencies_l3:
            return {"mean_ms": 0.0, "p50_ms": 0.0, "p90_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0, "count": 0}

        sorted_lat = sorted(self.latencies_l3)
        n = len(sorted_lat)
        return {
            "mean_ms": round(sum(sorted_lat) / n, 2),
            "p50_ms": round(sorted_lat[int(n * 0.50)], 2),
            "p90_ms": round(sorted_lat[min(int(n * 0.90), n - 1)], 2),
            "p95_ms": round(sorted_lat[min(int(n * 0.95), n - 1)], 2),
            "max_ms": round(sorted_lat[-1], 2),
            "count": n
        }

    def reset_call(self, call_id: str):
        """Cleans up call state."""
        self.suppression_engine.reset_call(call_id)
        self.active_nudges = [n for n in self.active_nudges if n.call_id != call_id]


nudge_engine = NudgeEngine()
