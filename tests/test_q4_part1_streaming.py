import pytest
import asyncio
import time

from q4.audio.streaming import AudioChunk
from q4.audio.replay import RealtimeCallReplayer, SAMPLE_CALLS
from q4.asr.streaming_asr import StreamingASREngine, TranscriptChunk
from q4.conversation.buffer import ConversationBuffer
from q4.conversation.state import LiveCallState


@pytest.mark.asyncio
async def test_realtime_call_replayer_chunking():
    replayer = RealtimeCallReplayer(chunk_duration_ms=100.0, time_scale=0.0)  # zero sleep for fast unit test
    turns = [
        {"speaker": "agent", "text": "Hello, how can I help you today?"},
        {"speaker": "customer", "text": "I have another vehicle."}
    ]

    chunks = []
    async for chunk in replayer.stream_call("call_test_01", turns):
        chunks.append(chunk)

    assert len(chunks) >= 4
    assert chunks[0].speaker == "agent"
    assert chunks[0].channel == 0
    assert chunks[-1].speaker == "customer"
    assert chunks[-1].channel == 1
    assert any(c.is_turn_boundary for c in chunks)


@pytest.mark.asyncio
async def test_streaming_asr_latency_measurement():
    replayer = RealtimeCallReplayer(chunk_duration_ms=150.0, time_scale=0.0)
    asr = StreamingASREngine(simulated_processing_delay_ms=10.0)
    call_id = "call_test_latency"

    turn_data = [{"speaker": "customer", "text": "I actually have two cars on my policy."}]
    
    transcript_chunks = []
    async for chunk in replayer.stream_call(call_id, turn_data):
        res = asr.process_chunk(chunk)
        transcript_chunks.append(res)
        
        # Verify latency measurements exist on every chunk
        assert res.audio_received_at > 0
        assert res.asr_started_at >= res.audio_received_at
        assert res.asr_completed_at >= res.asr_started_at
        assert res.asr_latency_ms >= 5.0
        assert res.e2e_delay_ms >= res.asr_latency_ms

    assert transcript_chunks[-1].is_final is True
    assert "two cars" in transcript_chunks[-1].partial_text

    stats = asr.get_latency_stats()
    assert stats["count"] == len(transcript_chunks)
    assert stats["p50"] > 0
    assert stats["p95"] >= stats["p50"]


@pytest.mark.asyncio
async def test_speaker_separation_diarization():
    asr = StreamingASREngine(simulated_processing_delay_ms=0.0)
    
    chunk_agent = AudioChunk(
        call_id="call_diar",
        chunk_id="chunk_01",
        channel=0,
        speaker="agent",
        received_at=time.perf_counter(),
        is_turn_boundary=True,
        text_segment="Welcome to Darwix Insurance."
    )
    res_agent = asr.process_chunk(chunk_agent)
    assert res_agent.speaker == "agent"
    assert res_agent.is_final is True

    chunk_cust = AudioChunk(
        call_id="call_diar",
        chunk_id="chunk_02",
        channel=1,
        speaker="customer",
        received_at=time.perf_counter(),
        is_turn_boundary=True,
        text_segment="I have a question about my rate."
    )
    res_cust = asr.process_chunk(chunk_cust)
    assert res_cust.speaker == "customer"
    assert res_cust.is_final is True


@pytest.mark.asyncio
async def test_conversation_buffer_and_live_state():
    state = LiveCallState("call_state_001")
    asr = StreamingASREngine(simulated_processing_delay_ms=0.0)

    # Partial chunk
    chunk_1 = AudioChunk(
        call_id="call_state_001",
        chunk_id="c_1",
        channel=1,
        speaker="customer",
        received_at=time.perf_counter(),
        is_turn_boundary=False,
        text_segment="Actually I have"
    )
    res_1 = asr.process_chunk(chunk_1)
    turn_1 = state.ingest_transcript_chunk(res_1)
    assert turn_1 is None  # still partial
    assert "Actually I have" in state.buffer.active_partial.partial_text

    # Finalizing chunk
    chunk_2 = AudioChunk(
        call_id="call_state_001",
        chunk_id="c_2",
        channel=1,
        speaker="customer",
        received_at=time.perf_counter(),
        is_turn_boundary=True,
        text_segment="another vehicle."
    )
    res_2 = asr.process_chunk(chunk_2)
    turn_2 = state.ingest_transcript_chunk(res_2)
    assert turn_2 is not None  # finalized turn
    assert turn_2.speaker == "customer"
    assert turn_2.text == "Actually I have another vehicle."
    assert len(state.buffer.turns) == 1

    summary = state.get_summary()
    assert summary["turn_count"] == 1
    assert summary["active_topic"] == "auto_insurance"
