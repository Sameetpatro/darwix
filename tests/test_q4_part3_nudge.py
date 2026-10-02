import pytest
import time
from q4.conversation.buffer import ConversationTurn
from q4.conversation.state import LiveCallState
from q4.signals.models import ConversationSignal, SignalType, SignalSeverity
from q4.nudge.models import NudgeEvent
from q4.nudge.cooldown import CooldownManager
from q4.nudge.suppression import SuppressionEngine
from q4.nudge.priority import PriorityManager, NudgePriority
from q4.nudge.generator import NudgeGenerator
from q4.nudge.engine import NudgeEngine
from q4.delivery.websocket import WebSocketDeliveryManager


@pytest.fixture
def call_state():
    return LiveCallState(call_id="call_test_nudge_001")


@pytest.fixture
def custom_cooldown():
    return CooldownManager(default_cooldown_seconds=10.0)


@pytest.fixture
def suppression_eng(custom_cooldown):
    return SuppressionEngine(
        min_confidence_threshold=0.75,
        cooldown_seconds=10.0,
        cooldown_mgr=custom_cooldown
    )


@pytest.mark.asyncio
async def test_confidence_threshold_suppression(call_state, suppression_eng):
    """
    Suppression Rule 1: Confidence threshold check.
    Signal with confidence < 0.75 must be suppressed.
    """
    low_conf_signal = ConversationSignal(
        call_id=call_state.call_id,
        type=SignalType.CROSS_SELL_OPPORTUNITY.value,
        speaker="customer",
        confidence=0.55,  # Below 0.75 threshold
        evidence="I... uh... maybe... another...",
        topic="vehicle_insurance"
    )

    result = suppression_eng.evaluate(low_conf_signal, call_state)
    assert not result.should_nudge
    assert result.suppressed
    assert result.rule == "CONFIDENCE_THRESHOLD"

    high_conf_signal = ConversationSignal(
        call_id=call_state.call_id,
        type=SignalType.CROSS_SELL_OPPORTUNITY.value,
        speaker="customer",
        confidence=0.91,  # Above 0.75 threshold
        evidence="Actually, I have another vehicle too.",
        topic="vehicle_insurance"
    )
    result_high = suppression_eng.evaluate(high_conf_signal, call_state)
    assert result_high.should_nudge
    assert not result_high.suppressed


@pytest.mark.asyncio
async def test_duplicate_suppression(call_state, suppression_eng):
    """
    Suppression Rule 2: Duplicate check.
    The exact same signal evidence should not generate a second active nudge.
    """
    sig = ConversationSignal(
        call_id=call_state.call_id,
        type=SignalType.CROSS_SELL_OPPORTUNITY.value,
        speaker="customer",
        confidence=0.91,
        evidence="Actually, I have another vehicle too.",
        topic="vehicle_insurance"
    )

    # First evaluation: approved
    res1 = suppression_eng.evaluate(sig, call_state)
    assert res1.should_nudge

    # Mark as shown
    suppression_eng.mark_shown(sig)

    # Second evaluation with identical evidence: suppressed as duplicate
    res2 = suppression_eng.evaluate(sig, call_state)
    assert not res2.should_nudge
    assert res2.rule in ["DUPLICATE_SUPPRESSION", "COOLDOWN_ACTIVE"]


@pytest.mark.asyncio
async def test_cooldown_suppression(call_state, custom_cooldown):
    """
    Suppression Rule 3: Cooldown check.
    Different evidence of the same signal type within cooldown period should be suppressed.
    """
    supp_eng = SuppressionEngine(
        min_confidence_threshold=0.75,
        cooldown_seconds=5.0,
        cooldown_mgr=custom_cooldown
    )

    sig1 = ConversationSignal(
        call_id=call_state.call_id,
        type=SignalType.FRUSTRATION.value,
        speaker="customer",
        confidence=0.88,
        evidence="I've already explained this twice.",
        topic="customer_satisfaction"
    )
    res1 = supp_eng.evaluate(sig1, call_state)
    assert res1.should_nudge
    supp_eng.mark_shown(sig1)

    # Different text, same signal type within 5.0 seconds cooldown
    sig2 = ConversationSignal(
        call_id=call_state.call_id,
        type=SignalType.FRUSTRATION.value,
        speaker="customer",
        confidence=0.90,
        evidence="I already told you three times!",
        topic="customer_satisfaction"
    )
    res2 = supp_eng.evaluate(sig2, call_state)
    assert not res2.should_nudge
    assert res2.rule == "COOLDOWN_ACTIVE"

    # Simulate elapsed time beyond cooldown
    now_later = time.time() + 6.0
    is_cooling, _ = custom_cooldown.is_on_cooldown(
        call_id=call_state.call_id,
        signal_type=SignalType.FRUSTRATION.value,
        topic="customer_satisfaction",
        cooldown_seconds=5.0,
        current_time=now_later
    )
    assert not is_cooling


def test_priority_hierarchy_configuration():
    """
    Rule 5: Priority configuration test.
    Priorities must not be blindly hardcoded; they must be configurable.
    """
    pm = PriorityManager()
    assert pm.get_priority("compliance_gap") == "high"
    assert pm.get_priority("cross_sell_opportunity") == "medium"
    assert pm.get_priority("info") == "low"

    # Dynamic reconfiguration at runtime
    pm.set_priority("cross_sell_opportunity", "critical")
    assert pm.get_priority("cross_sell_opportunity") == "critical"


@pytest.mark.asyncio
async def test_nudge_generator_short_formatting(call_state):
    """
    Verifies that generated nudges follow the concise Q4 template:
    Headline, Context, Message directive, TTL expiration.
    """
    generator = NudgeGenerator()
    sig = ConversationSignal(
        call_id=call_state.call_id,
        type=SignalType.COMPLIANCE_GAP.value,
        speaker="customer",
        confidence=0.96,
        evidence="Call reached binding stage without mandatory disclosure",
        topic="compliance",
        severity=SignalSeverity.HIGH.value
    )

    nudge = await generator.generate_nudge(sig, call_state, use_deepseek=False)
    assert nudge.headline == "COMPLIANCE"
    assert "disclosure" in nudge.message.lower()
    assert nudge.priority == "high"
    assert nudge.expires_in == 15
    assert nudge.generation_latency_ms >= 0.0


@pytest.mark.asyncio
async def test_websocket_delivery_latency():
    """
    Verifies that WebSocket delivery tracks L4 latency and computes statistics.
    """
    ws_mgr = WebSocketDeliveryManager()
    nudge = NudgeEvent(
        call_id="call_ws_test",
        priority="high",
        type="compliance_gap",
        headline="COMPLIANCE",
        context="Required disclosure has not been given.",
        message="Provide the required disclosure before continuing.",
        confidence=0.96,
        expires_in=15
    )

    # Deliver with 0 active connections (local memory loop)
    l4_ms = await ws_mgr.broadcast_nudge(nudge)
    assert l4_ms >= 0.0

    stats = ws_mgr.get_latency_stats()
    assert "p50_ms" in stats
    assert "p95_ms" in stats
    assert stats["count"] == 1


@pytest.mark.asyncio
async def test_end_to_end_nudge_engine_pipeline(call_state):
    """
    End-to-end integration:
    Signal -> Nudge Engine (Suppression -> DeepSeek Generator -> L3 measurement)
    """
    engine = NudgeEngine()
    engine.reset_call(call_state.call_id)

    sig = ConversationSignal(
        call_id=call_state.call_id,
        type=SignalType.CROSS_SELL_OPPORTUNITY.value,
        speaker="customer",
        confidence=0.91,
        evidence="I actually have another vehicle too.",
        topic="vehicle_insurance"
    )

    # 1. Process valid signal
    nudge = await engine.process_signal(sig, call_state, use_deepseek=False)
    assert nudge is not None
    assert nudge.headline == "CROSS-SELL"
    assert "multi-vehicle" in nudge.message.lower()
    assert nudge.priority == "medium"

    # 2. Process duplicate signal -> must be suppressed
    nudge_dup = await engine.process_signal(sig, call_state, use_deepseek=False)
    assert nudge_dup is None

    # Check suppression stats
    supp_stats = engine.get_suppression_stats()
    assert supp_stats["total_nudges_generated"] == 1
    assert supp_stats["total_signals_suppressed"] == 1
