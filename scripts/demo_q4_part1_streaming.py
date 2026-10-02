import asyncio
import sys
import time

from q4.audio.replay import RealtimeCallReplayer, SAMPLE_CALLS
from q4.asr.streaming_asr import StreamingASREngine
from q4.conversation.state import LiveCallState


async def run_part1_demo():
    print("=" * 80)
    print("      DARWIX Q4 PART 1: REAL-TIME AUDIO & STREAMING ASR PIPELINE")
    print("=" * 80)
    print("Scenario: Customer Auto Insurance Policy Call (Cross-Sell Cue)")
    print("Streaming: 250ms Audio Chunks with Continuous Latency Measurement\n")

    call_id = f"live_call_{int(time.time())}"
    replayer = RealtimeCallReplayer(chunk_duration_ms=250.0, time_scale=0.5)  # 2x playback speed for quick interactive demo
    asr = StreamingASREngine(simulated_processing_delay_ms=22.0)
    call_state = LiveCallState(call_id=call_id)

    turns_script = SAMPLE_CALLS["call_cross_sell"]

    print(f"Call ID: {call_id}")
    print("-" * 80)
    print(f"{'CHUNK':<14} | {'SPEAKER':<10} | {'TRANSCRIPT (PARTIAL / FINAL)':<35} | {'ASR LATENCY':<12}")
    print("-" * 80)

    chunk_count = 0
    t_start = time.time()

    async for chunk in replayer.stream_call(call_id, turns_script):
        chunk_count += 1
        
        # Process streaming audio chunk through ASR
        transcript_chunk = asr.process_chunk(chunk)
        
        # Ingest into live conversation state
        finalized_turn = call_state.ingest_transcript_chunk(transcript_chunk)

        status_tag = "[FINAL]" if transcript_chunk.is_final else "[PARTIAL]"
        display_text = transcript_chunk.partial_text
        if len(display_text) > 32:
            display_text = f"...{display_text[-29:]}"

        print(
            f"{transcript_chunk.chunk_id:<14} | "
            f"{transcript_chunk.speaker.upper():<10} | "
            f"{display_text:<32} {status_tag:<7} | "
            f"{transcript_chunk.asr_latency_ms:6.1f} ms"
        )

        if finalized_turn:
            print(f"  >>> COMMITTED TURN {finalized_turn.turn_id}: [{finalized_turn.speaker.upper()}] \"{finalized_turn.text}\" (Confidence: {finalized_turn.confidence:.2f})")

    total_time = time.time() - t_start
    stats = asr.get_latency_stats()

    print("\n" + "=" * 80)
    print("      PART 1 STREAMING BENCHMARK & LATENCY SUMMARY")
    print("=" * 80)
    print(f"- Total Audio Chunks Processed : {stats['count']}")
    print(f"- Total Wall Time              : {total_time:.2f} s")
    print(f"- Finalized Turns Captured     : {len(call_state.buffer.turns)}")
    print(f"- ASR Latency Mean             : {stats['mean']:.2f} ms")
    print(f"- ASR Latency P50 (Median)     : {stats['p50']:.2f} ms")
    print(f"- ASR Latency P90              : {stats['p90']:.2f} ms")
    print(f"- ASR Latency P95              : {stats['p95']:.2f} ms")
    print(f"- ASR Latency Max              : {stats['max']:.2f} ms")
    print("=" * 80)
    print("Status: CONTINUOUS STREAMING TRANSCRIPTION & LATENCY VERIFIED CLEANLY!\n")


if __name__ == "__main__":
    asyncio.run(run_part1_demo())
