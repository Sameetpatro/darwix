import time
from typing import Optional
from pydantic import BaseModel, Field


class AudioChunk(BaseModel):
    """
    Represents an atomic audio chunk in a real-time streaming pipeline.
    Standard telephony/WebRTC chunk duration is typically 100ms - 250ms.
    """
    call_id: str = Field(..., description="Unique active call identifier")
    chunk_id: str = Field(..., description="Unique chunk sequence identifier")
    sequence: int = Field(0, description="Monotonically increasing sequence number")
    channel: int = Field(1, description="Audio channel (0=Agent/PBX, 1=Customer/Telephony)")
    speaker: str = Field("customer", description="'customer' or 'agent'")
    duration_ms: float = Field(250.0, description="Chunk length in milliseconds")
    received_at: float = Field(default_factory=time.perf_counter, description="Monotonic timestamp when chunk arrived")
    raw_bytes: Optional[bytes] = Field(None, description="Raw PCM/WAV payload if available")
    is_speech: bool = Field(True, description="VAD flag: speech vs ambient background noise")
    is_turn_boundary: bool = Field(False, description="True if speaker stopped speaking or turn ended")
    text_segment: Optional[str] = Field(None, description="Acoustic text segment for real-time streaming simulation")
