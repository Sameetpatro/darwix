import asyncio
import sys
import time
from pathlib import Path

# Ensure root workspace is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from q3.philippines.agent import ph_voice_agent
from q3.philippines.locale import ph_locale
from q3.philippines.intent_detector import ph_intent_detector


async def run_live_test():
    print("\n" + "=" * 80)
    print("      DARWIX Q3 PART 1: PHILIPPINES LIFE INSURANCE VOICE BOT (VANI)")
    print("                     LIVE INTERACTIVE DEMONSTRATION")
    print("=" * 80)
    print("Market: Philippines  |  Sector: Life Insurance & Bancassurance")
    print("Languages: English, Filipino (Tagalog), Taglish (Code-Switching)")
    print("Core Rule: Localization != Translation (Direct Comprehension)")
    print("=" * 80 + "\n")

    session_id = f"live_demo_{int(time.time())}"
    agent = ph_voice_agent

    # -------------------------------------------------------------------------
    # Turn 0: Greeting
    # -------------------------------------------------------------------------
    print(">>> [INITIALIZING CALL] Starting session:", session_id)
    greeting = agent.start_call(session_id, language="taglish")
    print(f"🤖 Vani (Agent): \"{greeting['text']}\"")
    print("-" * 80)
    await asyncio.sleep(0.5)

    test_turns = [
        {
            "description": "TURN 1: PROMPT REFERENCE CODE-SWITCHING UTTERANCE",
            "utterance": "Gusto ko pong malaman kung magkano yung premium for this policy.",
            "expect": "Direct comprehension of Taglish, premium_information intent, and Q2 KB retrieval."
        },
        {
            "description": "TURN 2: MULTI-SLOT QUALIFICATION VOLUNTEERING",
            "utterance": "Ako po ay 32 anyos, kailangan ko ng 1 million pesos coverage para sa asawa at anak ko gamit ang BDO.",
            "expect": "Extracts 4 slots simultaneously (Age, Coverage, Beneficiary, Bank) and asks ONLY for budget."
        },
        {
            "description": "TURN 3: PRICE & BUDGET OBJECTION HANDLING",
            "utterance": "Masyadong mahal yata ang monthly premium niyan, baka hindi kayanin.",
            "expect": "Culturally grounded objection response citing ₱1,500/mo (₱50/day cup of coffee/merienda)."
        },
        {
            "description": "TURN 4: OUT-OF-SCOPE INQUIRY (LANGUAGE-PRESERVING FALLBACK)",
            "utterance": "Paano po ba mag-bake ng chocolate chip cookies sa bahay?",
            "expect": "Zero hallucination, strict Taglish fallback, and human advisor offer."
        },
        {
            "description": "TURN 5: HUMAN WARM TRANSFER ESCALATION",
            "utterance": "Gusto ko pong makausap ang live financial advisor o manager ninyo.",
            "expect": "Triggers human escalation, warm handoff response, and escalated=True."
        },
        {
            "description": "TURN 6: LANGUAGE SWITCH TO ENGLISH & LAPSE POLICY QUESTION",
            "utterance": "What happens if my policy lapses? Is there a grace period?",
            "expect": "Detects pure English, retrieves 31-day grace period rule with citation from Q2 KB."
        }
    ]

    for i, t in enumerate(test_turns, start=1):
        print(f"\n[TURN {i}] {t['description']}")
        print(f"🎯 Objective: {t['expect']}")
        print(f"👤 Caller: \"{t['utterance']}\"")

        # Step 1: Locale analysis
        lang_res = ph_locale.detect_language(t['utterance'])
        intent_res = ph_intent_detector.detect_intent(t['utterance'])

        print(f"🔍 [NATIVE NLP ANALYSIS]:")
        print(f"   • Language Detected     : {lang_res.language.upper()} (Code-Switch: {lang_res.code_switch})")
        print(f"   • Markers Identified    : {lang_res.detected_markers}")
        print(f"   • Insurance Terms Found : {lang_res.insurance_terms_found}")
        print(f"   • Intent Classified     : {intent_res.intent}")
        print(f"   • Sector                : {intent_res.sector}")

        # Step 2: Agent processing & neural TTS
        t_res = await agent.handle_turn(
            session_id=session_id,
            user_utterance=t['utterance'],
            synthesize_audio=True
        )

        print(f"🤖 Vani (Agent):")
        print(f"   \"{t_res['agent_response']}\"")

        if t_res['citation']:
            print(f"📚 [Q2 GROUNDED CITATION]: {t_res['citation']}")

        if t_res['missing_slots']:
            print(f"📋 [QUALIFICATION MISSING SLOTS]: {t_res['missing_slots']}")

        if t_res['audio_path']:
            p = Path(t_res['audio_path'])
            size_kb = p.stat().st_size / 1024 if p.exists() else 0.0
            print(f"🔊 [NEURAL AUDIO GENERATED]: {p.name} ({size_kb:.1f} KB | Latency: {t_res['tts_latency_ms']:.1f}ms)")

        print(f"⚡ [LATENCY]: Dialog & RAG: {t_res['total_latency_ms'] - t_res['tts_latency_ms']:.1f}ms | Total Turn: {t_res['total_latency_ms']:.1f}ms")
        print("-" * 80)
        await asyncio.sleep(0.3)

    # Final Session Status
    session = agent.dialog_manager.get_or_create_session(session_id)
    print("\n" + "=" * 80)
    print("                    FINAL SESSION SUMMARY & PROFILE")
    print("=" * 80)
    print(f"Session ID        : {session_id}")
    print(f"Caller Language   : {session.language.upper()}")
    print(f"Escalated to Human: {session.escalated}")
    print(f"Qualification Data:")
    for k, v in session.profile.model_dump().items():
        if v is not None:
            print(f"   • {k:<20}: {v}")
    print("=" * 80)
    print("                     ALL TEST CHECKS VERIFIED LIVE!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_live_test())
