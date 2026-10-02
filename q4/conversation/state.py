import time
from typing import Dict, Any, List, Set, Optional
from pydantic import BaseModel, Field

from q4.conversation.buffer import ConversationBuffer, ConversationTurn
from q4.asr.streaming_asr import TranscriptChunk


class LiveCallState:
    """
    Maintains the live conversation state across the entire call duration.
    Tracks speaker turns, compliance stages, disclosures given, and latency logs.
    """

    def __init__(self, call_id: str):
        self.call_id = call_id
        self.status: str = "active"
        self.start_time: float = time.time()
        self.buffer = ConversationBuffer(call_id)
        
        # State tracking
        self.stage: str = "greeting"  # greeting, discovery, quote, binding, closing
        self.active_topic: Optional[str] = None
        self.disclosures_given: Set[str] = set()
        self.turn_count: int = 0
        self.chunk_latencies: List[float] = []
        self.signals: List[Dict[str, Any]] = []

    def add_signal(self, signal: Any):
        """Records a detected signal in call history."""
        sig_data = signal.model_dump() if hasattr(signal, "model_dump") else signal
        self.signals.append(sig_data)

    def ingest_transcript_chunk(self, chunk: TranscriptChunk) -> Optional[ConversationTurn]:
        """Ingests a streaming ASR chunk and updates call state."""
        self.chunk_latencies.append(chunk.asr_latency_ms)
        finalized_turn = self.buffer.update_from_chunk(chunk)

        if finalized_turn:
            self.turn_count += 1
            self._update_stage_from_turn(finalized_turn)

        return finalized_turn

    def _update_stage_from_turn(self, turn: ConversationTurn):
        """Monitors conversational progression across stages."""
        text_lower = turn.text.lower()

        # Track compliance disclosures spoken by the agent
        if turn.speaker == "agent":
            if any(term in text_lower for term in ["license disclosure", "california insurance disclosure", "call is recorded", "terms and conditions"]):
                self.disclosures_given.add("mandatory_disclosure")
            if "multi-vehicle" in text_lower or "add another vehicle" in text_lower:
                self.disclosures_given.add("multi_vehicle_offered")

        # Track call progression
        if any(term in text_lower for term in ["finalize", "bind", "binding", "charge", "payment deposit", "continue"]):
            if self.stage != "closing":
                self.stage = "binding_ready"

        if "vehicle" in text_lower or "car" in text_lower:
            self.active_topic = "auto_insurance"

    def get_summary(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "status": self.status,
            "duration_sec": round(time.time() - self.start_time, 1),
            "turn_count": len(self.buffer.turns),
            "stage": self.stage,
            "disclosures_given": list(self.disclosures_given),
            "active_topic": self.active_topic,
            "signals_detected": len(self.signals),
            "signals": self.signals,
            "turns": [t.model_dump() for t in self.buffer.turns]
        }

