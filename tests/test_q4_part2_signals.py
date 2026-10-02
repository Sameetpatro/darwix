import pytest
import time
from q4.conversation.buffer import ConversationTurn
from q4.conversation.state import LiveCallState
from q4.signals.models import ConversationSignal, SignalType, SignalSeverity
from q4.signals.engine import SignalDetectionEngine
from q4.jev.laya_signal_classifier import LayaSignalClassifier


@pytest.fixture
def call_state():
    return LiveCallState(call_id="call_test_q4_001")


@pytest.fixture
def signal_engine():
    return SignalDetectionEngine()


def test_cross_sell_opportunity_detection(call_state, signal_engine):
    """
    Test 1: Customer explicitly mentions another vehicle.
    Customer: 'Actually, I have another vehicle too.'
    Expected: cross_sell_opportunity, confidence >= 0.90, speaker='customer'
    """
    turn = ConversationTurn(
        turn_id="turn_01",
        call_id=call_state.call_id,
        speaker="customer",
        text="Actually, I have another vehicle too.",
        start_timestamp=10.0,
        end_timestamp=12.5,
        turn_index=1
    )
    call_state.buffer.turns.append(turn)

    signals = signal_engine.process_turn(turn, call_state)
    assert len(signals) >= 1
    
    cross_sell_sig = next((s for s in signals if s.type == SignalType.CROSS_SELL_OPPORTUNITY.value), None)
    assert cross_sell_sig is not None
    assert cross_sell_sig.speaker == "customer"
    assert cross_sell_sig.confidence >= 0.90
    assert "vehicle" in cross_sell_sig.evidence.lower()
    assert cross_sell_sig.topic == "vehicle_insurance"
    assert cross_sell_sig.status == "new"
    assert cross_sell_sig.detection_latency_ms >= 0.0


def test_cross_sell_false_positive_rejection(call_state, signal_engine):
    """
    Contrast Test: 3rd-party mention should not trigger a high-confidence cross-sell.
    Customer: 'My brother has another vehicle.'
    Expected: Low confidence (< 0.50) or suppressed
    """
    turn = ConversationTurn(
        turn_id="turn_02",
        call_id=call_state.call_id,
        speaker="customer",
        text="My brother has another vehicle.",
        start_timestamp=14.0,
        end_timestamp=16.0,
        turn_index=2
    )
    call_state.buffer.turns.append(turn)

    classifier = LayaSignalClassifier()
    is_valid, reason, conf = classifier._evaluate_cross_sell(turn.text, "customer")
    assert not is_valid
    assert conf < 0.50
    assert "3rd party" in reason.lower()


def test_noisy_ambiguous_speech_rejection(call_state, signal_engine):
    """
    Ambiguous / noisy speech:
    Customer: 'I... uh... maybe... another...'
    Expected: Low confidence (< 0.50) -> Must not trigger confident signal
    """
    classifier = LayaSignalClassifier()
    conf, reason = classifier.evaluate_signal_confidence("cross_sell_opportunity", "I... uh... maybe... another...", "customer")
    assert conf < 0.50
    assert "ambiguous" in reason.lower() or "suppressed" in reason.lower()


def test_compliance_gap_detection(call_state, signal_engine):
    """
    Test 2: Customer pushes to continue/binding, but agent omitted mandatory disclosure.
    Customer: 'Okay, let's continue.'
    Expected: compliance_gap, confidence >= 0.95, severity='high'
    """
    turn = ConversationTurn(
        turn_id="turn_03",
        call_id=call_state.call_id,
        speaker="customer",
        text="Okay, let's continue.",
        start_timestamp=20.0,
        end_timestamp=22.0,
        turn_index=3
    )
    call_state.buffer.turns.append(turn)

    signals = signal_engine.process_turn(turn, call_state)
    comp_sig = next((s for s in signals if s.type == SignalType.COMPLIANCE_GAP.value), None)
    assert comp_sig is not None
    assert comp_sig.confidence >= 0.95
    assert comp_sig.severity == SignalSeverity.HIGH.value
    assert comp_sig.topic == "compliance"
    assert "mandatory_disclosure" in comp_sig.metadata.get("missing_disclosure")


def test_compliance_fulfilled_by_agent(call_state, signal_engine):
    """
    If agent fulfills disclosure before customer continues, no compliance gap should be emitted.
    """
    agent_turn = ConversationTurn(
        turn_id="turn_04",
        call_id=call_state.call_id,
        speaker="agent",
        text="Before we bind, please note this call is recorded and subject to California Insurance Disclosure terms and conditions.",
        start_timestamp=23.0,
        end_timestamp=28.0,
        turn_index=4
    )
    signal_engine.process_turn(agent_turn, call_state)
    assert "mandatory_disclosure" in call_state.disclosures_given

    cust_turn = ConversationTurn(
        turn_id="turn_05",
        call_id=call_state.call_id,
        speaker="customer",
        text="Okay, let's continue.",
        start_timestamp=29.0,
        end_timestamp=31.0,
        turn_index=5
    )
    signals = signal_engine.process_turn(cust_turn, call_state)
    comp_sig = next((s for s in signals if s.type == SignalType.COMPLIANCE_GAP.value), None)
    assert comp_sig is None  # FULFILLED! No gap.


def test_rising_frustration_detection(call_state, signal_engine):
    """
    Test 3: Customer expresses frustration with repeated questions.
    Customer: 'I already told you this three times.'
    Expected: frustration signal, confidence >= 0.85, severity='high'
    """
    turn = ConversationTurn(
        turn_id="turn_06",
        call_id=call_state.call_id,
        speaker="customer",
        text="I already told you this three times. I don't understand why you're asking again.",
        start_timestamp=35.0,
        end_timestamp=39.0,
        turn_index=6
    )
    call_state.buffer.turns.append(turn)

    signals = signal_engine.process_turn(turn, call_state)
    frust_sig = next((s for s in signals if s.type == SignalType.FRUSTRATION.value), None)
    assert frust_sig is not None
    assert frust_sig.confidence >= 0.85
    assert frust_sig.severity == SignalSeverity.HIGH.value
    assert frust_sig.topic == "customer_satisfaction"
    assert "already told you this three times" in frust_sig.evidence


def test_payment_difficulty_detection(call_state, signal_engine):
    """
    Test 4: Customer states payment difficulty.
    Customer: "I don't think I can make the payment this month."
    Expected: payment_difficulty, confidence >= 0.90, severity='high'
    """
    turn = ConversationTurn(
        turn_id="turn_07",
        call_id=call_state.call_id,
        speaker="customer",
        text="I don't think I can make the payment this month.",
        start_timestamp=42.0,
        end_timestamp=45.0,
        turn_index=7
    )
    call_state.buffer.turns.append(turn)

    signals = signal_engine.process_turn(turn, call_state)
    pay_sig = next((s for s in signals if s.type == SignalType.PAYMENT_DIFFICULTY.value), None)
    assert pay_sig is not None
    assert pay_sig.confidence >= 0.90
    assert pay_sig.severity == SignalSeverity.HIGH.value
    assert pay_sig.topic == "billing_and_payments"


def test_signal_engine_latency_measurement(call_state, signal_engine):
    """
    Verifies that signal engine captures L2 latency and calculates summary statistics.
    """
    turn = ConversationTurn(
        turn_id="turn_lat",
        call_id=call_state.call_id,
        speaker="customer",
        text="Actually, I have another vehicle too.",
        start_timestamp=50.0,
        end_timestamp=52.0,
        turn_index=8
    )
    signal_engine.process_turn(turn, call_state)

    stats = signal_engine.get_latency_stats()
    assert "mean_ms" in stats
    assert "p50_ms" in stats
    assert "p95_ms" in stats
    assert stats["count"] >= 1
    assert stats["max_ms"] >= 0.0


def test_structured_signal_schema_compliance():
    """
    Validates the exact required Q4 JSON schema.
    """
    sig = ConversationSignal(
        signal_id="sig_001",
        call_id="call_123",
        timestamp=1742.4,
        type="cross_sell_opportunity",
        speaker="customer",
        confidence=0.91,
        evidence="I have another vehicle too.",
        topic="vehicle_insurance",
        status="new"
    )
    data = sig.model_dump()
    assert data["signal_id"] == "sig_001"
    assert data["call_id"] == "call_123"
    assert data["timestamp"] == 1742.4
    assert data["type"] == "cross_sell_opportunity"
    assert data["speaker"] == "customer"
    assert data["confidence"] == 0.91
    assert data["evidence"] == "I have another vehicle too."
    assert data["topic"] == "vehicle_insurance"
    assert data["status"] == "new"
