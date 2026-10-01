#!/usr/bin/env python3
"""
Autonomous Benchmark Suite for Darwix Voice Agent (Vani)
Executes 3 complete, multi-turn end-to-end voice calls:
1. Cooperative Pre-Qualification Call
2. Objection Handling & FAQ Knowledge Base Call
3. Out-of-Scope Fallback & High-Leverage Conflict Call

Generates:
- Audio recordings in recordings/
- Structured JSON and TXT transcripts in transcripts/
- Benchmark summary metrics in data/benchmarks_summary.json
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List

from app.pipeline import VoicePipeline
from app.config import settings
from app.logging_config import logger


SCENARIOS = [
    {
        "scenario_id": "call_1_cooperative_prequal",
        "title": "Scenario 1: Cooperative Customer Pre-Qualification",
        "caller_id": "michael_chang_austin",
        "expected_behavior": (
            "Agent greets caller as Vani from Darwix, systematically collects all 9 qualification fields, "
            "confirms details, and delivers an instant PRE_QUALIFIED underwriting decision."
        ),
        "turns": [
            "Hello! My name is Michael Chang and my business is Horizon Tech Services LLC.",
            "We have been operating for 3 years and our average monthly revenue is $65,000.",
            "We are looking for $150,000 to invest in equipment upgrades and team expansion.",
            "We have no existing debt loans, and we are based in Austin, Texas.",
            "Yes, all those details are completely accurate.",
        ],
    },
    {
        "scenario_id": "call_2_objections_and_faqs",
        "title": "Scenario 2: Objection Handling & Knowledge Base Inquiries",
        "caller_id": "elena_rostova_seattle",
        "expected_behavior": (
            "Agent answers prepayment penalty FAQ and funding timeline FAQ with exact knowledge base citations, "
            "then seamlessly transitions to collecting qualification data and pre-qualifies the applicant."
        ),
        "turns": [
            "Hi there, before I apply, are there any prepayment penalties if I pay off the loan early?",
            "And how fast can I get funded once I submit everything?",
            "That is wonderful. My name is Elena Rostova with BlueWave Logistics Corp.",
            "We do $80,000 monthly, in business 5 years, need $200,000 for fleet expansion in Seattle, Washington, no existing loans.",
            "Yes, that sounds correct.",
        ],
    },
    {
        "scenario_id": "call_3_fallback_and_high_leverage",
        "title": "Scenario 3: Out-of-Scope Strict Fallback & Unrealistic Loan Leverage",
        "caller_id": "daniel_price_chicago",
        "expected_behavior": (
            "Agent strictly delivers non-hallucination fallback on cryptocurrency inquiry, "
            "detects excessive loan-to-revenue leverage ratio ($1.5M requested on $12k/mo revenue = 125x), "
            "flags conflict, and routes application to NEEDS_REVIEW."
        ),
        "turns": [
            "Can I use this loan to invest in cryptocurrency tokens and Bitcoin mining?",
            "Okay, I understand. My name is Daniel Price, company is Swift Retail LLC in Chicago, Illinois.",
            "We have been in business for 8 months and make about $12,000 monthly revenue.",
            "We want to borrow $1,500,000 for working capital.",
            "No existing loans.",
        ],
    },
]


async def run_scenario(pipeline: VoicePipeline, scenario: Dict[str, Any]) -> Dict[str, Any]:
    call_id = scenario["scenario_id"]
    caller_id = scenario["caller_id"]
    logger.info("=================================================================")
    logger.info("STARTING BENCHMARK: %s (%s)", scenario["title"], call_id)
    logger.info("=================================================================")

    start_res = await pipeline.initialize_call(call_id=call_id, caller_id=caller_id)
    session = pipeline.session_manager.get_session(call_id)

    turn_results = []
    for idx, user_text in enumerate(scenario["turns"], 1):
        turn_start = time.perf_counter()
        turn_res = await pipeline.process_user_speech(
            call_id=call_id,
            user_text=user_text,
            client_asr_duration_ms=110.0,
            confidence=0.98,
        )
        total_time_ms = (time.perf_counter() - turn_start) * 1000

        turn_results.append({
            "turn_index": idx,
            "customer_text": user_text,
            "agent_text": turn_res["agent_text"],
            "dialog_action": turn_res.get("dialog_action"),
            "kb_citation": turn_res.get("kb_citation"),
            "audio_url": turn_res.get("audio_url"),
            "latencies": turn_res.get("latencies"),
        })

    end_res = pipeline.end_call(call_id=call_id, reason="normal_completion")

    # Generate human readable TXT transcript
    txt_filename = f"{call_id}_transcript.txt"
    txt_path = settings.transcripts_dir / txt_filename
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"DARWIX AI VOICE CALL TRANSCRIPT\n")
        f.write(f"Call ID: {call_id}\n")
        f.write(f"Scenario: {scenario['title']}\n")
        f.write(f"Caller ID: {caller_id}\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write("=" * 70 + "\n\n")

        for turn in session.turns:
            speaker_label = "VANI (AGENT)" if turn.speaker == "agent" else "CALLER"
            citation_str = f" [Source: {turn.kb_citation}]" if turn.kb_citation else ""
            f.write(f"[{speaker_label} - Turn {turn.turn_id}]\n")
            f.write(f"{turn.text}{citation_str}\n")
            if turn.latencies and turn.latencies.total_roundtrip_ms > 0:
                f.write(f"Latency: Roundtrip={turn.latencies.total_roundtrip_ms}ms, LLM={turn.latencies.llm_ms}ms, TTS={turn.latencies.tts_ms}ms\n")
            f.write("\n")

        f.write("=" * 70 + "\n")
        f.write(f"FINAL CALL SUMMARY:\n")
        f.write(json.dumps(end_res, indent=2))

    return {
        "scenario_id": call_id,
        "title": scenario["title"],
        "expected_behavior": scenario["expected_behavior"],
        "total_turns": end_res.get("total_turns"),
        "customer_turns": end_res.get("customer_turns"),
        "agent_turns": end_res.get("agent_turns"),
        "avg_roundtrip_latency_ms": end_res.get("avg_roundtrip_latency_ms"),
        "avg_llm_latency_ms": end_res.get("avg_llm_latency_ms"),
        "avg_tts_latency_ms": end_res.get("avg_tts_latency_ms"),
        "loan_application": end_res.get("loan_application"),
        "audio_recordings": [t["audio_url"] for t in turn_results if t.get("audio_url")],
        "json_transcript_path": str(settings.transcripts_dir / f"{call_id}.json"),
        "txt_transcript_path": str(txt_path),
        "turns": turn_results,
    }


async def main():
    pipeline = VoicePipeline()
    benchmark_reports = []

    for scen in SCENARIOS:
        report = await run_scenario(pipeline, scen)
        benchmark_reports.append(report)

    output_path = Path(__file__).resolve().parent.parent / "data" / "benchmarks_summary.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "company": "Darwix",
            "agent": "Vani",
            "total_scenarios_evaluated": len(benchmark_reports),
            "scenarios": benchmark_reports,
        }, f, indent=2)

    logger.info("All benchmarks completed successfully! Results written to %s", output_path)
    print("\n=======================================================")
    print(f"BENCHMARKS COMPLETED: {len(benchmark_reports)} calls recorded.")
    print(f"Summary JSON: {output_path}")
    print("=======================================================\n")


if __name__ == "__main__":
    asyncio.run(main())
