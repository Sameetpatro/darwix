import time
import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class NudgeEvent(BaseModel):
    """
    Standardized payload for in-call nudges delivered to the agent dashboard.
    Adheres strictly to the Q4 Part 3 specification:
    {
      "event": "nudge",
      "nudge_id": "ndg_001",
      "call_id": "call_123",
      "priority": "high",
      "type": "compliance_gap",
      "headline": "COMPLIANCE",
      "context": "Required disclosure has not been given.",
      "message": "Provide the required disclosure before continuing.",
      "confidence": 0.94,
      "expires_in": 15,
      "timestamp": 1742.4
    }
    """
    event: str = "nudge"
    nudge_id: str = Field(default_factory=lambda: f"ndg_{uuid.uuid4().hex[:8]}")
    call_id: str
    priority: str = Field("medium", description="high, medium, low, critical")
    type: str = Field(..., description="Signal type that produced the nudge")
    headline: str = Field(..., description="Short category title: e.g. CROSS-SELL, COMPLIANCE, FRUSTRATION")
    context: str = Field(..., description="Brief context sentence explaining why the nudge was generated")
    message: str = Field(..., description="Ultra-concise action directive for the human agent (-> directive)")
    confidence: float = Field(..., ge=0.0, le=1.0)
    expires_in: int = Field(15, description="Time-To-Live in seconds before nudge self-expires")
    timestamp: float = Field(default_factory=lambda: round(time.time(), 2))
    signal_id: Optional[str] = None
    generation_latency_ms: float = 0.0
    status: str = "active"  # active, acknowledged, expired, suppressed


class SuppressionCheckResult(BaseModel):
    """Result of checking all suppression rules for a signal."""
    should_nudge: bool
    suppressed: bool
    reason: Optional[str] = None
    rule: Optional[str] = None
