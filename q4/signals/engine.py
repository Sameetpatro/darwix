import time
from typing import List, Optional, Dict, Any
from app.logging_config import logger
from q4.conversation.buffer import ConversationTurn
from q4.conversation.state import LiveCallState
from q4.signals.models import ConversationSignal, SignalType
from q4.signals.opportunities import opportunity_detector
from q4.signals.compliance import compliance_detector
from q4.signals.sentiment import sentiment_detector
from q4.signals.intent import intent_detector


class SignalDetectionEngine:
    """
    Coordinates real-time signal detection across conversation turns.
    Measures Latency L2: ASR Turn -> Signal Detection.
    Converts raw transcript turns into structured conversation signals.
    """

    def __init__(self):
        self.opportunity_detector = opportunity_detector
        self.compliance_detector = compliance_detector
        self.sentiment_detector = sentiment_detector
        self.intent_detector = intent_detector
        
        # History & metrics
        self.detected_signals: List[ConversationSignal] = []
        self.detection_latencies: List[float] = []

    def process_turn(self, turn: ConversationTurn, state: LiveCallState) -> List[ConversationSignal]:
        """
        Processes a newly committed conversation turn, runs all detectors,
        and records extraction latency L2.
        """
        start_time = time.perf_counter()
        emitted_signals: List[ConversationSignal] = []

        # 1. Cross-sell opportunity detection
        opp_sig = self.opportunity_detector.detect(turn, state)
        if opp_sig:
            emitted_signals.append(opp_sig)

        # 2. Compliance gap detection
        comp_sig = self.compliance_detector.detect(turn, state)
        if comp_sig:
            emitted_signals.append(comp_sig)

        # 3. Rising frustration detection
        sent_sig = self.sentiment_detector.detect(turn, state)
        if sent_sig:
            emitted_signals.append(sent_sig)

        # 4. Payment difficulty & intent detection
        intent_sig = self.intent_detector.detect(turn, state)
        if intent_sig:
            emitted_signals.append(intent_sig)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        self.detection_latencies.append(latency_ms)

        # Attach L2 latency to every signal
        for sig in emitted_signals:
            sig.detection_latency_ms = latency_ms
            self.detected_signals.append(sig)
            logger.info(
                "[SIGNAL_ENGINE] Detected '%s' (Conf: %.2f, Severity: %s, Latency: %.2f ms): %s",
                sig.type, sig.confidence, sig.severity, latency_ms, sig.evidence
            )

        return emitted_signals

    def get_latency_stats(self) -> Dict[str, float]:
        """Calculates percentile distribution for L2 signal extraction latency."""
        if not self.detection_latencies:
            return {"mean_ms": 0.0, "p50_ms": 0.0, "p90_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}

        sorted_lat = sorted(self.detection_latencies)
        n = len(sorted_lat)
        return {
            "mean_ms": round(sum(sorted_lat) / n, 2),
            "p50_ms": round(sorted_lat[int(n * 0.50)], 2),
            "p90_ms": round(sorted_lat[min(int(n * 0.90), n - 1)], 2),
            "p95_ms": round(sorted_lat[min(int(n * 0.95), n - 1)], 2),
            "max_ms": round(sorted_lat[-1], 2),
            "count": n
        }


signal_engine = SignalDetectionEngine()
