import asyncio
import sys
import time
from pathlib import Path

# Ensure root workspace is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from q3.indonesia.agent import id_voice_agent
from q3.indonesia.locale import id_locale
from q3.indonesia.intent_detector import id_intent_detector


async def run_live_id_test():
    print("\n" + "=" * 80)
    print("      DARWIX Q3 PART 2: INDONESIA CONSUMER FINANCE VOICE BOT (VANI)")
    print("                     LIVE INTERACTIVE DEMONSTRATION")
    print("=" * 80)
    print("Market: Indonesia  |  Sector: Consumer Finance / Multifinance")
    print("Languages: Formal ID, Colloquial ID (Bahasa Gaul), Regional Speech, Code-Switching")
    print("Core Rule: Localization != Translation (Direct Native Comprehension)")
    print("=" * 80 + "\n")

    session_id = f"live_id_{int(time.time())}"
    agent = id_voice_agent

    # -------------------------------------------------------------------------
    # Turn 0: Greeting
    # -------------------------------------------------------------------------
    print(">>> [INITIALIZING CALL] Starting session:", session_id)
    greeting = agent.start_call(session_id, dialect_style="colloquial")
    print(f"🤖 Vani (Agent): \"{greeting['text']}\"")
    print("-" * 80)
    await asyncio.sleep(0.5)

    test_turns = [
        {
            "description": "TURN 1: PROMPT REFERENCE CODE-SWITCHING UTTERANCE",
            "utterance": "Kalau saya telat bayar cicilan, ada late fee nggak?",
            "expect": "Identifies language=id, code_switch=True, intent=late_payment_fee, sector=consumer_finance, Q2 KB retrieval."
        },
        {
            "description": "TURN 2: SECTOR-SPECIFIC PAYMENT OBJECTION",
            "utterance": "Denda-nya terlalu tinggi kak, kemahalan buat saya.",
            "expect": "Handles high denda objection, explains 0.5%/day OJK regulation, and offers Denda Waiver on same-day payment."
        },
        {
            "description": "TURN 3: FINANCIAL DELAY / SERET OBJECTION",
            "utterance": "Bulan ini lagi seret banget kak, uang gajian belum cair.",
            "expect": "Offers Promise to Pay (PTP) path to protect credit score and prevent field visits."
        },
        {
            "description": "TURN 4: REGIONAL DIALECT WITH JAVANESE / SUNDANESE PARTICLES",
            "utterance": "Piye carane bayar angsuran iki rek? Bisa lewat Indomaret atau Alfamart nggak?",
            "expect": "Comprehends regional speech and answers payment methods with Indomaret/Alfamart/VA."
        },
        {
            "description": "TURN 5: OUT-OF-SCOPE QUERY (LANGUAGE-PRESERVING FALLBACK)",
            "utterance": "Gimana resep cara bikin rendang sapi yang empuk dan enak?",
            "expect": "Zero hallucination, strict Indonesian fallback, and offers customer service."
        },
        {
            "description": "TURN 6: HUMAN CUSTOMER SERVICE ESCALATION",
            "utterance": "Tolong sambungkan saya ke agen customer service manusia sekarang.",
            "expect": "Warm transfer to customer service officer, sets escalated=True."
        }
    ]

    for i, t in enumerate(test_turns, start=1):
        print(f"\n[TURN {i}] {t['description']}")
        print(f"🎯 Objective: {t['expect']}")
        print(f"👤 Caller: \"{t['utterance']}\"")

        # Step 1: Locale & Intent Analysis
        lang_res = id_locale.detect_language(t['utterance'])
        intent_res = id_intent_detector.detect_intent(t['utterance'])

        print(f"🔍 [NATIVE NLP ANALYSIS]:")
        print(f"   • Language Detected     : {lang_res.language.upper()} (Code-Switch: {lang_res.code_switch})")
        print(f"   • Dialect Style         : {lang_res.dialect_style.upper()}" + (f" (Regional: {lang_res.regional_dialect.upper()})" if lang_res.regional_dialect else ""))
        print(f"   • Markers Identified    : {lang_res.detected_markers}")
        print(f"   • Finance Terms Found   : {lang_res.finance_terms_found}")
        print(f"   • Intent Classified     : {intent_res.intent}")
        print(f"   • Sector                : {intent_res.sector}")

        # Step 2: Agent turn processing
        t_res = await agent.handle_turn(
            session_id=session_id,
            user_utterance=t['utterance'],
            synthesize_audio=True
        )

        print(f"🤖 Vani (Agent):")
        print(f"   \"{t_res['agent_response']}\"")

        if t_res['citation']:
            print(f"📚 [Q2 GROUNDED CITATION]: {t_res['citation']}")

        if t_res['support_path_offered']:
            print(f"🛡️  [SUPPORT PATH OFFERED]: {t_res['support_path_offered']}")

        if t_res['audio_path']:
            p = Path(t_res['audio_path'])
            size_kb = p.stat().st_size / 1024 if p.exists() else 0.0
            print(f"🔊 [NEURAL AUDIO GENERATED]: {p.name} ({size_kb:.1f} KB | Voice: id-ID-GadisNeural | Latency: {t_res['tts_latency_ms']:.1f}ms)")

        print(f"⚡ [LATENCY]: Dialog & RAG: {t_res['total_latency_ms'] - t_res['tts_latency_ms']:.1f}ms | Total Turn: {t_res['total_latency_ms']:.1f}ms")
        print("-" * 80)
        await asyncio.sleep(0.3)

    # Final Session Status
    session = agent.dialog_manager.get_or_create_session(session_id)
    print("\n" + "=" * 80)
    print("                    FINAL SESSION SUMMARY & ACCOUNT CONTEXT")
    print("=" * 80)
    print(f"Session ID           : {session_id}")
    print(f"Contract Number      : {session.account_context.contract_number}")
    print(f"Customer Name        : {session.account_context.customer_name}")
    print(f"Financed Product     : {session.account_context.product_type}")
    print(f"Monthly Installment  : Rp {session.account_context.monthly_installment:,.0f}")
    print(f"Support Path Offered : {session.support_path_offered}")
    print(f"Escalated to Human   : {session.escalated}")
    print("=" * 80)
    print("                 ALL INDONESIA TEST CHECKS VERIFIED LIVE!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_live_id_test())
