import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List

from q3.philippines.agent import PhilippinesVoiceAgent
from q3.indonesia.agent import IndonesianVoiceAgent
from q3.philippines.tts import PhilippinesTTSEngine
from q3.indonesia.tts import IndonesianTTSEngine

BASE_DIR = Path(__file__).resolve().parent.parent
REC_PH_DIR = BASE_DIR / "recordings" / "philippines"
REC_ID_DIR = BASE_DIR / "recordings" / "indonesia"
TR_PH_DIR = BASE_DIR / "transcripts" / "philippines"
TR_ID_DIR = BASE_DIR / "transcripts" / "indonesia"

REC_PH_DIR.mkdir(parents=True, exist_ok=True)
REC_ID_DIR.mkdir(parents=True, exist_ok=True)
TR_PH_DIR.mkdir(parents=True, exist_ok=True)
TR_ID_DIR.mkdir(parents=True, exist_ok=True)

ph_agent = PhilippinesVoiceAgent()
id_agent = IndonesianVoiceAgent()
ph_tts = PhilippinesTTSEngine()
id_tts = IndonesianTTSEngine()


# =============================================================================
# SCENARIOS DEFINITIONS
# =============================================================================

PH_SCENARIOS = [
    {
        "case_id": "ph_case_1_cooperative",
        "title": "Case 1: Cooperative Caller (Full Qualification Flow)",
        "description": "Caller completes full life insurance qualification cleanly in Filipino/Taglish, setting age, coverage, budget, beneficiary, and bank partner.",
        "turns": [
            "Magandang araw po! Nais ko pong kumuha ng term life insurance para sa aking sarili.",
            "Ako po ay 32 years old.",
            "Kailangan ko po ng 2 million pesos na coverage para sa pamilya ko.",
            "Kaya ko pong magbayad ng around 2,500 pesos monthly.",
            "Ang ilalagay kong beneficiary ay ang aking asawa at dalawang anak.",
            "BDO po ang aking payroll bank account."
        ]
    },
    {
        "case_id": "ph_case_2_objection",
        "title": "Case 2: Caller with Objections (Handled with Localized Framing)",
        "description": "Caller expresses budget concerns and fear of company bankruptcy; agent handles with ₱1,500/mo (₱50/day cup of coffee) and Insurance Commission protection guarantee.",
        "turns": [
            "Gusto ko sanang kumuha ng life insurance pero medyo nag-aalangan ako.",
            "Medyo pricey kasi, wala pa akong budget ngayon para sa monthly premium.",
            "Baka naman malugi o mawala lang yung pera ko dyan sa kompanya ninyo?"
        ]
    },
    {
        "case_id": "ph_case_3_mixed_language",
        "title": "Case 3: Mixed-Language Conversation (Taglish & English Code-Switching)",
        "description": "Caller fluidly mixes English technical financial terms with Tagalog grammar regarding riders, grace period, and policy lapses.",
        "turns": [
            "Hello po, I would like to inquire about your term life insurance packages.",
            "Gusto ko pong malaman kung magkano yung premium for this policy if I add a critical illness rider?",
            "Kung mag-lapse ba yung policy ko, is there a 31-day grace period to settle the balance?"
        ]
    },
    {
        "case_id": "ph_case_4_human_escalation",
        "title": "Case 4: Caller Requesting Human Assistance (Warm Transfer)",
        "description": "Caller asks complex estate planning questions and requests a human licensed financial advisor.",
        "turns": [
            "Magandang araw po. May mga specific legal questions po ako tungkol sa trust fund at estate tax ng policy.",
            "Pwede po bang kumausap ng live agent or licensed financial advisor ngayon?"
        ]
    },
    {
        "case_id": "ph_case_5_unsupported_fallback",
        "title": "Case 5: Caller Asking Unsupported / Out-of-Scope Questions (Strict Fallback)",
        "description": "Caller asks out-of-scope non-financial questions (cookie baking, crypto trading); agent adheres to strict anti-hallucination fallback in polite Taglish.",
        "turns": [
            "Magandang araw! Pwede po bang magtanong?",
            "Can you teach me how to bake homemade chocolate chip cookies with melted butter?",
            "May cryptocurrency trading o bitcoin investments din ba kayo dito sa Darwix?"
        ]
    }
]

ID_SCENARIOS = [
    {
        "case_id": "id_case_1_cooperative",
        "title": "Case 1: Cooperative Caller (Clean Inquiry and Resolution)",
        "description": "Customer inquires about contract details, installment amount, and due date, resolved cleanly via Q2 KB and installment context.",
        "turns": [
            "Selamat siang, saya ingin menanyakan rincian cicilan dan tanggal jatuh tempo pembiayaan motor saya.",
            "Nomor kontrak saya MF-2026-9921.",
            "Bisa tolong sebutkan nominal angsuran bulan ini dan cara pembayarannya?"
        ]
    },
    {
        "case_id": "id_case_2_sector_objection",
        "title": "Case 2: Sector-Specific Objection (High Late Fee / Denda Waiver Request)",
        "description": "Customer objects to high late penalty fee after 3 days overdue; agent offers approved Denda Waiver procedure if principal is settled today.",
        "turns": [
            "Halo admin, ini soal denda angsuran motor saya.",
            "Denda-nya terlalu tinggi kak! Masa saya baru telat 3 hari dendanya udah segitu? Bisa minta waiver atau potongan denda nggak?",
            "Oke kalau gitu saya transfer pokok angsurannya sekarang lewat m-Banking."
        ]
    },
    {
        "case_id": "id_case_3_code_switching",
        "title": "Case 3: Code-Switching Conversation (Indonesian + English Finance Terms)",
        "description": "Customer combines Indonesian syntax with English finance terminology (late fee, grace period, reschedule tenor).",
        "turns": [
            "Siang kak, mau clarify soal cicilan mobil saya.",
            "Kalau saya telat bayar cicilan, ada late fee nggak? Dan apakah ada grace period sebelum kena penalty?",
            "Bisa nggak kalau saya reschedule tenor angsuran saya jadi tiga puluh enam bulan?"
        ]
    },
    {
        "case_id": "id_case_4_colloquial_slang",
        "title": "Case 4: Highly Colloquial Caller (Bahasa Gaul, Particles & Financial Hardship)",
        "description": "Customer uses informal colloquial particles (dong, sih, kan, nih, deh) and reports cash delay ('lagi seret'); agent grants Promise to Pay (PTP).",
        "turns": [
            "Halo kak, mau nanya dong soal cicilan motor saya yang jatuh tempo besok gimana ya?",
            "Aduh kak, duit saya lagi seret banget nih bulan ini, belum gajian juga. Nggak bisa bayar besok gimana dong?",
            "Wah makasih banyak ya kak, ntar tanggal 22 saya lunasin angsurannya."
        ]
    },
    {
        "case_id": "id_case_5_human_escalation",
        "title": "Case 5: Caller Requesting Human Assistance (Warm Transfer)",
        "description": "Customer inquires about total loss vehicle insurance dispute and requests immediate transfer to customer service debt counselor.",
        "turns": [
            "Halo, selamat siang.",
            "Saya ada masalah sengketa klaim asuransi total loss kendaraan saya, bisa tolong sambungkan ke staf manusia atau customer service debt counselor sekarang?"
        ]
    },
    {
        "case_id": "id_case_6_regional_speaker",
        "title": "Case 6: Regional Indonesian Speaker (Javanese & Sundanese Speech Patterns)",
        "description": "Customer uses East Javanese (piye, rek, monggo) and Sundanese (kumaha, teh, euy) dialect markers; agent comprehends directly without failure.",
        "turns": [
            "Piye carane bayar angsuran iki rek? Monggo infone.",
            "Kumaha lamun kuring hayang pelunasan dipercepat motor teh euy, aya diskon bunga teu?"
        ]
    }
]


# =============================================================================
# RUNNER LOGIC
# =============================================================================

async def run_philippines_scenarios():
    print("\n" + "=" * 80)
    print("      RUNNING PHILIPPINES EVALUATION SCENARIOS (5 CASES)")
    print("=" * 80)

    for case in PH_SCENARIOS:
        print(f"\n>>> Executing {case['title']}...")
        session_id = f"eval_{case['case_id']}_{int(time.time())}"
        
        # Start call session
        start_res = ph_agent.start_call(session_id)
        bot_audio_segments = []

        transcript_md = f"# Philippines Voice Bot Transcript\n\n"
        transcript_md += f"## Call Metadata\n"
        transcript_md += f"- **Case ID**: `{case['case_id']}`\n"
        transcript_md += f"- **Scenario Title**: {case['title']}\n"
        transcript_md += f"- **Description**: {case['description']}\n"
        transcript_md += f"- **Market**: Philippines (Life Insurance / Bancassurance)\n"
        transcript_md += f"- **Primary TTS Voice**: `fil-PH-BlessicaNeural`\n"
        transcript_md += f"- **Session ID**: `{session_id}`\n\n"
        transcript_md += f"---\n\n## Conversation Transcript\n\n"

        # Initial Greeting
        greet_text = start_res["text"]
        transcript_md += f"### Turn 0 (Initial Bot Greeting)\n"
        transcript_md += f"**Vani**: \"{greet_text}\"\n\n"
        transcript_md += f"- **Language**: `{start_res.get('language', 'taglish')}`\n"
        bot_audio_segments.append(greet_text)

        last_profile = {}
        for idx, user_utt in enumerate(case["turns"], 1):
            print(f"  Turn {idx}: Customer: \"{user_utt[:50]}...\"")
            turn_res = await ph_agent.handle_turn(session_id, user_utt)
            resp_text = turn_res["agent_response"]
            bot_audio_segments.append(resp_text)
            last_profile = turn_res.get("qualification_profile", {})

            transcript_md += f"### Turn {idx}\n"
            transcript_md += f"**Customer**: \"{user_utt}\"\n\n"
            transcript_md += f"**Vani**: \"{resp_text}\"\n\n"
            transcript_md += f"#### Turn Metadata\n"
            transcript_md += f"- **Detected Language / Dialect**: `{turn_res.get('language')}`\n"
            transcript_md += f"- **Intent Detected**: `{turn_res.get('intent')}`\n"
            transcript_md += f"- **Escalated to Human**: `{turn_res.get('escalated', False)}`\n"
            transcript_md += f"- **Qualification Completed**: `{turn_res.get('completed', False)}`\n"
            transcript_md += f"- **Turn Latency**: `{turn_res.get('total_latency_ms', 0):.1f} ms` (TTS: `{turn_res.get('tts_latency_ms', 0):.1f} ms`)\n"
            
            # Entities
            transcript_md += f"- **Current Profile Slots**: `{json.dumps(last_profile, ensure_ascii=False)}`\n"
            transcript_md += f"- **Missing Slots**: `{json.dumps(turn_res.get('missing_slots', []), ensure_ascii=False)}`\n"

            # Knowledge retrieved
            evidence = turn_res.get("evidence", [])
            if evidence:
                transcript_md += f"- **Knowledge Retrieved ({len(evidence)} chunks)**:\n"
                for c in evidence[:3]:
                    transcript_md += f"  - [{c.get('chunk_id')}] Score: `{c.get('score')}` | Source: `{c.get('source')}` | Content: *\"{c.get('text', '')[:120]}...\"*\n"
                if turn_res.get("citation"):
                    transcript_md += f"- **Citation**: `{turn_res.get('citation')}`\n"
            else:
                transcript_md += f"- **Knowledge Retrieved**: `None (Deterministic Underwriting / Direct Intent Logic)`\n"

            transcript_md += f"- **Turn Audio**: `{turn_res.get('audio_path')}`\n\n"

        # Final Profile Status
        transcript_md += f"### Final Underwriting Profile\n"
        transcript_md += f"```json\n{json.dumps(last_profile, indent=2, ensure_ascii=False)}\n```\n"

        # Write transcript
        tr_file = TR_PH_DIR / f"{case['case_id']}.md"
        with open(tr_file, "w", encoding="utf-8") as f:
            f.write(transcript_md)

        # Synthesize consolidated scenario audio file
        full_dialogue_speech = " ... ".join(bot_audio_segments)
        audio_file_name = f"{case['case_id']}.mp3"
        await ph_tts.synthesize(
            text=full_dialogue_speech,
            language="taglish",
            output_filename=audio_file_name
        )
        audio_file = REC_PH_DIR / audio_file_name
        print(f"  -> Generated Transcript: {tr_file.name}")
        print(f"  -> Generated Consolidated Audio: {audio_file.name} ({audio_file.stat().st_size} bytes)")


async def run_indonesia_scenarios():
    print("\n" + "=" * 80)
    print("      RUNNING INDONESIA EVALUATION SCENARIOS (6 CASES)")
    print("=" * 80)

    for case in ID_SCENARIOS:
        print(f"\n>>> Executing {case['title']}...")
        session_id = f"eval_{case['case_id']}_{int(time.time())}"
        
        # Start call session
        start_res = id_agent.start_call(session_id)
        bot_audio_segments = []

        transcript_md = f"# Indonesia Voice Bot Transcript\n\n"
        transcript_md += f"## Call Metadata\n"
        transcript_md += f"- **Case ID**: `{case['case_id']}`\n"
        transcript_md += f"- **Scenario Title**: {case['title']}\n"
        transcript_md += f"- **Description**: {case['description']}\n"
        transcript_md += f"- **Market**: Indonesia (Consumer Finance / Multifinance)\n"
        transcript_md += f"- **Primary TTS Voice**: `id-ID-GadisNeural`\n"
        transcript_md += f"- **Session ID**: `{session_id}`\n\n"
        transcript_md += f"---\n\n## Conversation Transcript\n\n"

        # Initial Greeting
        greet_text = start_res["text"]
        transcript_md += f"### Turn 0 (Initial Bot Greeting)\n"
        transcript_md += f"**Vani**: \"{greet_text}\"\n\n"
        transcript_md += f"- **Language**: `{start_res.get('language', 'id')}`\n"
        transcript_md += f"- **Dialect Style**: `{start_res.get('dialect_style', 'colloquial')}`\n"
        bot_audio_segments.append(greet_text)

        last_context = {}
        for idx, user_utt in enumerate(case["turns"], 1):
            print(f"  Turn {idx}: Customer: \"{user_utt[:50]}...\"")
            turn_res = await id_agent.handle_turn(session_id, user_utt)
            resp_text = turn_res["agent_response"]
            bot_audio_segments.append(resp_text)
            last_context = turn_res.get("account_context", {})

            transcript_md += f"### Turn {idx}\n"
            transcript_md += f"**Customer**: \"{user_utt}\"\n\n"
            transcript_md += f"**Vani**: \"{resp_text}\"\n\n"
            transcript_md += f"#### Turn Metadata\n"
            transcript_md += f"- **Detected Language**: `{turn_res.get('language')}`\n"
            transcript_md += f"- **Dialect Style**: `{turn_res.get('dialect_style')}`\n"
            transcript_md += f"- **Intent Detected**: `{turn_res.get('intent')}`\n"
            transcript_md += f"- **Escalated to Human**: `{turn_res.get('escalated', False)}`\n"
            transcript_md += f"- **Support Path Offered**: `{turn_res.get('support_path_offered')}`\n"
            transcript_md += f"- **Turn Latency**: `{turn_res.get('total_latency_ms', 0):.1f} ms` (TTS: `{turn_res.get('tts_latency_ms', 0):.1f} ms`)\n"
            
            # Account Context
            transcript_md += f"- **Account Context**: `{json.dumps(last_context, ensure_ascii=False)}`\n"

            # Knowledge retrieved
            evidence = turn_res.get("evidence", [])
            if evidence:
                transcript_md += f"- **Knowledge Retrieved ({len(evidence)} chunks)**:\n"
                for c in evidence[:3]:
                    transcript_md += f"  - [{c.get('chunk_id')}] Score: `{c.get('score')}` | Source: `{c.get('source')}` | Content: *\"{c.get('text', '')[:120]}...\"*\n"
                if turn_res.get("citation"):
                    transcript_md += f"- **Citation**: `{turn_res.get('citation')}`\n"
            else:
                transcript_md += f"- **Knowledge Retrieved**: `None (Deterministic Installment Context / Direct Intent Logic)`\n"

            transcript_md += f"- **Turn Audio**: `{turn_res.get('audio_path')}`\n\n"

        # Final Context Status
        transcript_md += f"### Final Multifinance Account State\n"
        transcript_md += f"```json\n{json.dumps(last_context, indent=2, ensure_ascii=False)}\n```\n"

        # Write transcript
        tr_file = TR_ID_DIR / f"{case['case_id']}.md"
        with open(tr_file, "w", encoding="utf-8") as f:
            f.write(transcript_md)

        # Synthesize consolidated scenario audio file
        full_dialogue_speech = " ... ".join(bot_audio_segments)
        audio_file_name = f"{case['case_id']}.mp3"
        await id_tts.synthesize(
            text=full_dialogue_speech,
            output_filename=audio_file_name
        )
        audio_file = REC_ID_DIR / audio_file_name
        print(f"  -> Generated Transcript: {tr_file.name}")
        print(f"  -> Generated Consolidated Audio: {audio_file.name} ({audio_file.stat().st_size} bytes)")


async def main():
    await run_philippines_scenarios()
    await run_indonesia_scenarios()
    print("\n" + "=" * 80)
    print("  ALL 11 EVALUATION SCENARIOS COMPLETED, RECORDED & TRANSCRIBED!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

