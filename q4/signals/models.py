import time
import uuid
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class SignalType(str, Enum):
    CROSS_SELL_OPPORTUNITY = "cross_sell_opportunity"
    COMPLIANCE_GAP = "compliance_gap"
    FRUSTRATION = "frustration"
    PAYMENT_DIFFICULTY = "payment_difficulty"
    INTENT = "intent"
    INFO = "info"


class SignalSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConversationSignal(BaseModel):
    """
    Common structured schema for real-time conversation signals.
    Follows the Q4 specification:
    {
      "signal_id": "sig_001",
      "call_id": "call_123",
      "timestamp": 1742.4,
      "type": "cross_sell_opportunity",
      "speaker": "customer",
      "confidence": 0.91,
      "evidence": "I have another vehicle too.",
      "topic": "vehicle_insurance",
      "status": "new"
    }
    """
    signal_id: str = Field(default_factory=lambda: f"sig_{uuid.uuid4().hex[:8]}")
    call_id: str = Field(..., description="ID of the active conversation")
    timestamp: float = Field(default_factory=lambda: round(time.time(), 2), description="Timestamp of signal generation")
    type: str = Field(..., description="Classification category (e.g. cross_sell_opportunity, compliance_gap, frustration, payment_difficulty)")
    speaker: str = Field("customer", description="Speaker associated with the signal (customer, agent, system)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    evidence: str = Field(..., description="Exact conversational utterance or state evidence")
    topic: str = Field("general", description="Categorical topic of the signal")
    severity: str = Field("medium", description="Priority/severity: low, medium, high, critical")
    status: str = Field("new", description="Signal lifecycle status: new, processed, suppressed, expired")
    detection_latency_ms: float = Field(0.0, description="Latency L2 in ms to detect the signal from transcript")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context metadata")
