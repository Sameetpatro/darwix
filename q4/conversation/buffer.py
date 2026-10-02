from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import time

from q4.asr.streaming_asr import TranscriptChunk


class ConversationTurn(BaseModel):
    """Represents a completed speaker turn in the conversation."""
    turn_id: str
    call_id: str
    speaker: str = Field(..., description="'customer' or 'agent'")
    text: str
    start_timestamp: float
    end_timestamp: float
    confidence: float = 0.95
    asr_latency_ms: float = 0.0
    turn_index: int = 0


class ConversationBuffer:
    """
    Buffers continuous streaming transcripts.
    Differentiates active partial speech from finalized conversation turns.
    """

    def __init__(self, call_id: str):
        self.call_id = call_id
        self.turns: List[ConversationTurn] = []
        self.active_partial: Optional[TranscriptChunk] = None
        self._turn_counter: int = 0
        self._start_time: float = time.time()

    def update_from_chunk(self, chunk: TranscriptChunk) -> Optional[ConversationTurn]:
        """
        Ingests a transcript chunk.
        If chunk is partial, updates active_partial.
        If chunk is final, seals the turn, adds it to turns history, and returns it.
        """
        self.active_partial = chunk

        if chunk.is_final and chunk.partial_text.strip():
            self._turn_counter += 1
            turn = ConversationTurn(
                turn_id=f"turn_{self._turn_counter:03d}",
                call_id=self.call_id,
                speaker=chunk.speaker,
                text=chunk.partial_text.strip(),
                start_timestamp=round(chunk.timestamp - 1.0, 3),
                end_timestamp=chunk.timestamp,
                confidence=chunk.confidence,
                asr_latency_ms=chunk.asr_latency_ms,
                turn_index=self._turn_counter
            )
            self.turns.append(turn)
            self.active_partial = None
            return turn

        return None

    def get_full_transcript(self, window_turns: Optional[int] = None) -> str:
        """Returns the formatted conversation transcript."""
        target_turns = self.turns[-window_turns:] if window_turns else self.turns
        lines = [f"{t.speaker.upper()}: {t.text}" for t in target_turns]
        
        if self.active_partial and self.active_partial.partial_text.strip():
            lines.append(f"{self.active_partial.speaker.upper()} (speaking...): {self.active_partial.partial_text.strip()}")

        return "\n".join(lines)

    def get_latest_turn(self) -> Optional[ConversationTurn]:
        return self.turns[-1] if self.turns else None
