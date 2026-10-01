import pytest
from app.state import CallSession, LatencyBreakdown, session_manager


def test_session_lifecycle():
    call_id = "test_call_001"
    session = session_manager.create_session(call_id=call_id, caller_id="test_caller")

    assert session.call_id == call_id
    assert session.status == "in-progress"
    assert len(session.turns) == 0

    # Add customer turn
    t1 = session.add_turn(
        speaker="customer",
        text="Hello, I need a business loan.",
        latencies=LatencyBreakdown(asr_ms=120.0, total_roundtrip_ms=120.0),
    )
    assert t1.turn_id == 1
    assert len(session.turns) == 1

    # Add agent turn
    t2 = session.add_turn(
        speaker="agent",
        text="Hi there! I can help with that.",
        audio_url="/recordings/test.mp3",
        latencies=LatencyBreakdown(llm_ms=250.0, tts_ms=180.0, total_roundtrip_ms=430.0),
    )
    assert t2.turn_id == 2
    assert len(session.turns) == 2

    # Verify LLM messages format
    messages = session.get_llm_messages(system_prompt="System Prompt")
    assert messages[0] == {"role": "system", "content": "System Prompt"}
    assert messages[1] == {"role": "user", "content": "Hello, I need a business loan."}
    assert messages[2] == {"role": "assistant", "content": "Hi there! I can help with that."}

    # Verify metrics
    metrics = session.get_summary_metrics()
    assert metrics["total_turns"] == 2
    assert metrics["customer_turns"] == 1
    assert metrics["agent_turns"] == 1
    assert metrics["avg_roundtrip_latency_ms"] == 430.0

    # Complete call
    session.complete_call(status="completed")
    assert session.status == "completed"
    assert session.end_time is not None
