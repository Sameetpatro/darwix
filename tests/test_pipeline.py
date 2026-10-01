from pathlib import Path
import pytest
from app.pipeline import VoicePipeline


@pytest.mark.asyncio
async def test_full_pipeline_flow():
    pipeline = VoicePipeline()
    call_id = "test_pipeline_001"

    # Step 1: Initialize call & Greeting
    init_res = await pipeline.initialize_call(call_id=call_id, caller_id="test_user")
    assert init_res["call_id"] == call_id
    assert init_res["turn_id"] == 1
    assert "Vani" in init_res["agent_text"]
    assert init_res["audio_url"] != ""
    assert init_res["latencies"]["tts_ms"] > 0

    # Step 2: Customer speaks
    turn_res = await pipeline.process_user_speech(
        call_id=call_id,
        user_text="Hi, I am interested in a business loan for my retail store.",
        client_asr_duration_ms=450.0,
        confidence=0.98,
    )
    assert turn_res["call_id"] == call_id
    assert turn_res["turn_id"] == 3  # Turn 1: agent greeting, Turn 2: customer, Turn 3: agent reply
    assert len(turn_res["agent_text"]) > 0
    assert turn_res["audio_url"].startswith("/recordings/")
    assert turn_res["latencies"]["asr_ms"] == 450.0
    assert turn_res["latencies"]["total_roundtrip_ms"] > 0

    # Step 3: End call
    summary = pipeline.end_call(call_id=call_id, reason="test_completed")
    assert summary["call_id"] == call_id
    assert summary["total_turns"] == 3
    assert summary["customer_turns"] == 1
    assert summary["agent_turns"] == 2

    # Clean up any generated recordings for this test
    recordings_dir = Path("recordings")
    if recordings_dir.exists():
        for f in recordings_dir.glob(f"{call_id}*.mp3"):
            f.unlink(missing_ok=True)
