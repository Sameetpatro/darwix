import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import numpy as np

from q4.audio.streaming import AudioChunk


class TranscriptChunk(BaseModel):
    """
    Structured transcript event emitted by the streaming ASR engine.
    Supports partial live hypotheses and committed final turns.
    """
    chunk_id: str
    call_id: str
    speaker: str = Field("customer", description="'customer' or 'agent'")
    partial_text: str = Field("", description="Accumulated utterance text for current turn")
    delta_text: str = Field("", description="Incremental token(s) added by this specific chunk")
    is_final: bool = Field(False, description="True when end-of-utterance or turn transition is reached")
    confidence: float = Field(0.95, description="ASR acoustic/language model confidence score [0.0 - 1.0]")
    
    # Precise Latency Tracking Metrics
    audio_received_at: float = Field(..., description="Monotonic timestamp when audio chunk was received")
    asr_started_at: float = Field(..., description="Monotonic timestamp when ASR processing began")
    asr_completed_at: float = Field(..., description="Monotonic timestamp when transcript hypothesis was emitted")
    asr_latency_ms: float = Field(..., description="Pure ASR processing latency: (completed - started) * 1000")
    e2e_delay_ms: float = Field(..., description="Total time from audio arrival to transcript: (completed - received) * 1000")
    timestamp: float = Field(default_factory=time.time, description="Wall clock timestamp")


class StreamingASREngine:
    """
    Streaming Automatic Speech Recognition (ASR) Engine.
    Converts real-time AudioChunk streams into continuous partial and final transcripts.
    Measures and logs exact millisecond latencies for every chunk.
    """

    def __init__(self, simulated_processing_delay_ms: float = 25.0):
        """
        :param simulated_processing_delay_ms: Realistic acoustic feature extraction & beam search latency.
        """
        self.simulated_processing_delay_ms = simulated_processing_delay_ms
        self._current_utterance: Dict[str, str] = {}  # call_id -> text
        self._current_speaker: Dict[str, str] = {}    # call_id -> speaker
        self._latency_history: List[float] = []

    def process_chunk(self, chunk: AudioChunk) -> TranscriptChunk:
        """
        Processes a single audio chunk and outputs an updated TranscriptChunk.
        Measures:
          audio_received (chunk.received_at)
                ↓
          ASR_started
                ↓
          ASR_completed
        """
        asr_started = time.perf_counter()

        # Speaker separation:
        # Channel 0 = Agent (PBX leg), Channel 1 = Customer (Telephony leg).
        # Fallback to chunk.speaker if channel metadata is unified.
        if chunk.channel == 0:
            speaker = "agent"
        elif chunk.channel == 1:
            speaker = "customer"
        else:
            speaker = chunk.speaker or "customer"

        call_id = chunk.call_id

        # Detect speaker switch or reset
        prev_speaker = self._current_speaker.get(call_id)
        if prev_speaker and prev_speaker != speaker:
            self._current_utterance[call_id] = ""

        self._current_speaker[call_id] = speaker

        # Extract delta text segment
        delta = (chunk.text_segment or "").strip()
        accum = self._current_utterance.get(call_id, "").strip()

        if delta:
            accum = f"{accum} {delta}".strip() if accum else delta

        self._current_utterance[call_id] = accum

        # Calculate confidence: penalize stutter / ambiguous tokens
        confidence = 0.94
        if "mumble" in accum.lower() or "uh..." in accum.lower():
            confidence = 0.45
        elif len(accum.split()) <= 2 and not chunk.is_turn_boundary:
            confidence = 0.82

        is_final = chunk.is_turn_boundary

        # Simulate acoustic search computation time
        if self.simulated_processing_delay_ms > 0:
            time.sleep(self.simulated_processing_delay_ms / 1000.0)

        asr_completed = time.perf_counter()
        asr_latency_ms = (asr_completed - asr_started) * 1000.0
        e2e_delay_ms = (asr_completed - chunk.received_at) * 1000.0

        self._latency_history.append(asr_latency_ms)

        result = TranscriptChunk(
            chunk_id=chunk.chunk_id,
            call_id=call_id,
            speaker=speaker,
            partial_text=accum,
            delta_text=delta,
            is_final=is_final,
            confidence=confidence,
            audio_received_at=chunk.received_at,
            asr_started_at=asr_started,
            asr_completed_at=asr_completed,
            asr_latency_ms=round(asr_latency_ms, 2),
            e2e_delay_ms=round(e2e_delay_ms, 2),
            timestamp=round(time.time(), 3)
        )

        # Clear buffer if turn finished
        if is_final:
            self._current_utterance[call_id] = ""

        return result

    def get_latency_stats(self) -> Dict[str, float]:
        """Calculates P50, P90, P95, mean, and max ASR latencies."""
        if not self._latency_history:
            return {"count": 0, "p50": 0.0, "p90": 0.0, "p95": 0.0, "mean": 0.0, "max": 0.0}

        arr = np.array(self._latency_history)
        return {
            "count": int(len(arr)),
            "p50": round(float(np.percentile(arr, 50)), 2),
            "p90": round(float(np.percentile(arr, 90)), 2),
            "p95": round(float(np.percentile(arr, 95)), 2),
            "mean": round(float(np.mean(arr)), 2),
            "max": round(float(np.max(arr)), 2),
        }


streaming_asr_engine = StreamingASREngine()

