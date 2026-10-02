import asyncio
import json
import time

from q4.audio.replay import RealtimeCallReplayer, SAMPLE_CALLS
from q4.asr.streaming_asr import StreamingASREngine
from q4.conversation.state import LiveCallState
from q4.signals.engine import SignalDetectionEngine


async def run_scenario(name: str, script_key: str):
    print("\n" + "=" * 85)
    print(f"  SCENARIO: {name.upper()}")
    print("=" * 85)

    call_id = f"call_{script_key}_{int(time.time())}"
    replayer = RealtimeCallReplayer(chunk_duration_ms=250.0, time_scale=0.2)  # fast pace for demo
    asr = StreamingASREngine(simulated_processing_delay_ms=18.0)
    call_state = LiveCallState(call_id=call_id)
    signal_engine = SignalDetectionEngine()

    turns_script = SAMPLE_CALLS.get(script_key, [])
    
    total_signals_detected = 0

    async for chunk in replayer.stream_call(call_id, turns_script):
        transcript_chunk = asr.process_chunk(chunk)
        finalized_turn = call_state.ingest_transcript_chunk(transcript_chunk)

        if finalized_turn:
            print(f"[{finalized_turn.speaker.upper()}] \"{finalized_turn.text}\"")
            
            # Run real-time signal detection on finalized turn
            signals = signal_engine.process_turn(finalized_turn, call_state)
            for sig in signals:
                total_signals_detected += 1
                call_state.add_signal(sig)
                print("\n  ⚡ [LIVE SIGNAL DETECTED]")
                print(f"     ID:         {sig.signal_id}")
                print(f"     Type:       {sig.type}")
                print(f"     Speaker:    {sig.speaker}")
                print(f"     Confidence: {sig.confidence:.2f}")
                print(f"     Severity:   {sig.severity}")
                print(f"     Evidence:   \"{sig.evidence}\"")
                print(f"     Topic:      {sig.topic}")
                print(f"     L2 Latency: {sig.detection_latency_ms:.2f} ms\n")

    stats = signal_engine.get_latency_stats()
    print(f"-> Result: {total_signals_detected} signal(s) detected. Mean L2 Latency: {stats.get('mean_ms', 0):.2f} ms")


async def main():
    print("*" * 85)
    print("      DARWIX Q4 PART 2: REAL-TIME CONVERSATION SIGNAL DETECTION ENGINE")
    print("*" * 85)
    print("Converts streaming transcripts into structured conversation events.")
    print("Detectors: Missed Cross-Sell | Compliance Gap | Rising Frustration | Payment Difficulty")

    await run_scenario("1. Missed Cross-Sell Opportunity", "call_cross_sell")
    await run_scenario("2. Compliance Gap", "call_compliance_gap")
    await run_scenario("3. Rising Frustration", "call_rising_frustration")
    await run_scenario("4. Payment Difficulty", "call_payment_difficulty")
    await run_scenario("5. False Positive Contrast (3rd Party)", "call_false_positive_cross_sell")
    await run_scenario("6. Ambiguous / Noisy Speech (Suppression)", "call_noisy_ambiguous")

    print("\n" + "*" * 85)
    print("      ALL Q4 PART 2 DEMONSTRATION SCENARIOS COMPLETED SUCCESSFULLY")
    print("*" * 85)


if __name__ == "__main__":
    asyncio.run(main())
