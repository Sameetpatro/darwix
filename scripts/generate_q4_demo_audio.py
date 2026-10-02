import asyncio
import json
import time
from pathlib import Path
import edge_tts
from q4.audio.replay import SAMPLE_CALLS

BASE_DIR = Path(__file__).resolve().parent.parent
REC_Q4_DIR = BASE_DIR / "recordings" / "q4"
TR_Q4_DIR = BASE_DIR / "transcripts" / "q4"

REC_Q4_DIR.mkdir(parents=True, exist_ok=True)
TR_Q4_DIR.mkdir(parents=True, exist_ok=True)

VOICE_AGENT = "en-US-JennyNeural"
VOICE_CUSTOMER = "en-US-GuyNeural"


async def synthesize_turn(text: str, voice: str, out_path: Path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


async def generate_q4_audio_and_transcripts():
    print("=" * 80)
    print("      GENERATING Q4 DEMO CALL AUDIO RECORDINGS & TRANSCRIPTS")
    print("=" * 80)

    for scenario_name, turns in SAMPLE_CALLS.items():
        print(f"\nProcessing scenario: {scenario_name} ({len(turns)} turns)...")
        combined_audio_bytes = bytearray()
        turn_records = []
        elapsed = 0.0

        for idx, turn in enumerate(turns, start=1):
            speaker = turn["speaker"]
            text = turn["text"]
            duration = round(len(text.split()) / 2.8 + 0.5, 1)
            voice = VOICE_AGENT if speaker == "agent" else VOICE_CUSTOMER
            temp_mp3 = REC_Q4_DIR / f"temp_{scenario_name}_{idx}.mp3"
            
            try:
                await synthesize_turn(text, voice, temp_mp3)
                if temp_mp3.exists():
                    audio_data = temp_mp3.read_bytes()
                    combined_audio_bytes.extend(audio_data)
                    temp_mp3.unlink()
            except Exception as exc:
                print(f"  Warning: synthesis failed for turn {idx}: {exc}")

            turn_records.append({
                "turn_index": idx,
                "speaker": speaker,
                "start_time": round(elapsed, 2),
                "end_time": round(elapsed + duration, 2),
                "duration": duration,
                "text": text
            })
            elapsed += duration

        # Save consolidated scenario audio
        final_mp3 = REC_Q4_DIR / f"{scenario_name}.mp3"
        if combined_audio_bytes:
            final_mp3.write_bytes(combined_audio_bytes)
            print(f"  -> Saved Audio: {final_mp3} ({len(combined_audio_bytes)} bytes)")

        # Save transcript JSON
        final_tr = TR_Q4_DIR / f"{scenario_name}.json"
        with open(final_tr, "w", encoding="utf-8") as f:
            json.dump({
                "scenario": scenario_name,
                "generated_at": time.time(),
                "turns_count": len(turn_records),
                "total_duration_sec": round(elapsed, 2),
                "turns": turn_records
            }, f, indent=2)
        print(f"  -> Saved Transcript: {final_tr}")

    print("\n" + "=" * 80)
    print("      ALL Q4 AUDIO & TRANSCRIPTS SUCCESSFULLY GENERATED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(generate_q4_audio_and_transcripts())
