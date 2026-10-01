import pytest
from fastapi.testclient import TestClient
from app.server import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["providers"]["llm"]["configured_provider"] == "deepseek"
    assert data["providers"]["tts"]["provider"] == "edge-tts"


def test_index_page_serves():
    response = client.get("/")
    assert response.status_code == 200
    assert "Darwix" in response.text
    assert "waveform-canvas" in response.text


def test_call_lifecycle_api():
    # 1. Start Call
    start_resp = client.post("/api/call/start", json={"caller_id": "test_web_user"})
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    call_id = start_data["call_id"]
    assert call_id.startswith("call_")
    assert len(start_data["agent_text"]) > 0
    assert start_data["audio_url"] != ""

    # 2. Turn
    turn_resp = client.post(
        "/api/call/turn",
        json={
            "call_id": call_id,
            "user_text": "I need a loan to expand my medical practice.",
            "client_asr_duration_ms": 320.0,
            "confidence": 0.95,
        },
    )
    assert turn_resp.status_code == 200
    turn_data = turn_resp.json()
    assert len(turn_data["agent_text"]) > 0
    assert turn_data["latencies"]["asr_ms"] == 320.0
    assert turn_data["latencies"]["total_roundtrip_ms"] > 0

    # 3. Retrieve Transcript
    transcript_resp = client.get(f"/api/call/{call_id}/transcript")
    assert transcript_resp.status_code == 200
    transcript_data = transcript_resp.json()
    assert transcript_data["call_id"] == call_id
    assert len(transcript_data["turns"]) == 3

    # 4. End Call
    end_resp = client.post("/api/call/end", json={"call_id": call_id, "reason": "test_end"})
    assert end_resp.status_code == 200
    end_data = end_resp.json()
    assert end_data["status"] == "test_end"

    # 5. List Calls
    calls_resp = client.get("/api/calls")
    assert calls_resp.status_code == 200
    calls_data = calls_resp.json()
    assert any(c["call_id"] == call_id for c in calls_data["calls"])
