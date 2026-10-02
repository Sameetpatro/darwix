import pytest
import os
import asyncio
from pathlib import Path

from q3.indonesia.locale import id_locale, IndonesiaLocaleEngine
from q3.indonesia.intent_detector import id_intent_detector
from q3.indonesia.account_context import IndonesianAccountContext
from q3.indonesia.objections import ph_or_id_objection_handler
from q3.indonesia.escalation import id_escalation_handler
from q3.indonesia.dialog_manager import id_dialog_manager
from q3.indonesia.agent import id_voice_agent
from q3.indonesia.tts import id_tts_engine


def test_language_identification_formal_indonesian():
    """Validates formal Bahasa Indonesia detection."""
    text = "Selamat siang, saya ingin menanyakan perihal ketentuan pembayaran denda keterlambatan angsuran pembiayaan saya."
    res = id_locale.detect_language(text)
    assert res.language == "id"
    assert res.dialect_style == "formal"
    assert "denda" in res.finance_terms_found
    assert "angsuran" in res.finance_terms_found


def test_language_identification_colloquial_indonesian():
    """Validates colloquial Indonesian (Bahasa Gaul) with conversational particles."""
    text = "Halo kak, mau nanya dong soal cicilan motor saya yang jatuh tempo besok gimana ya?"
    res = id_locale.detect_language(text)
    assert res.language == "id"
    assert res.dialect_style == "colloquial"
    assert "dong" in res.detected_markers or "kak" in res.detected_markers
    assert "cicilan" in res.finance_terms_found


def test_code_switching_english_finance_terms():
    """
    Validates the exact example from the prompt:
    'Kalau saya telat bayar cicilan, ada late fee nggak?'
    Expected:
    language = id
    code_switch = True
    intent = late_payment_fee
    sector = consumer_finance
    """
    text = "Kalau saya telat bayar cicilan, ada late fee nggak?"
    res = id_locale.detect_language(text)
    assert res.language == "id"
    assert res.code_switch is True
    assert "cicilan" in res.finance_terms_found

    intent_res = id_intent_detector.detect_intent(text)
    assert intent_res.language == "id"
    assert intent_res.code_switch is True
    assert intent_res.intent == "late_payment_fee"
    assert intent_res.sector == "consumer_finance"


def test_mandatory_finance_terminology_understanding():
    """
    Validates natural comprehension of all 7 mandatory terms:
    cicilan, tenor, denda, DP, jatuh tempo, angsuran, pembiayaan.
    """
    sample = (
        "Berapa minimal DP untuk pembiayaan motor ini? "
        "Bisa pilih tenor 24 bulan dengan angsuran cicilan tetap per bulan? "
        "Lalu kalau lewat jatuh tempo, kena denda berapa persen?"
    )
    terms = id_locale.extract_finance_terms(sample)
    expected = ["cicilan", "tenor", "denda", "dp", "jatuh tempo", "angsuran", "pembiayaan"]
    for exp in expected:
        assert exp in terms, f"Mandatory finance term '{exp}' missing from extraction"


def test_regional_indonesian_speech_markers():
    """Validates recognition of regional dialect particles (Javanese, Sundanese, Medan)."""
    # 1. Javanese regional marker
    jav_text = "Piye carane bayar cicilan iki rek? Monggo infone."
    jav_res = id_locale.detect_language(jav_text)
    assert jav_res.regional_dialect == "javanese"
    assert "piye" in jav_res.detected_markers or "rek" in jav_res.detected_markers

    # 2. Sundanese regional marker
    sun_text = "Kumaha cara bayar angsuran motor teh euy?"
    sun_res = id_locale.detect_language(sun_text)
    assert sun_res.regional_dialect == "sundanese"
    assert "teh" in sun_res.detected_markers or "euy" in sun_res.detected_markers

    # 3. Medan regional marker
    med_text = "Cemana cara perpanjang tenor pembiayaan kami ini wak?"
    med_res = id_locale.detect_language(med_text)
    assert med_res.regional_dialect == "medan"
    assert "cemana" in med_res.detected_markers or "wak" in med_res.detected_markers


def test_sector_specific_objection_handling():
    """
    Validates objection from prompt:
    'Denda-nya terlalu tinggi.'
    Must explain OJK regulation, 3-day grace period, and offer Denda Waiver on same-day payment.
    """
    text = "Denda-nya terlalu tinggi, keberatan saya."
    assert ph_or_id_objection_handler.is_objection(text)
    
    resp, support_path = ph_or_id_objection_handler.handle_objection(text, dialect_style="colloquial")
    assert support_path == "Denda Waiver Request"
    assert "0,5%" in resp
    assert "waiver" in resp.lower() or "penghapusan denda" in resp.lower()


def test_human_escalation_warm_transfer():
    """Validates escalation to customer service or debt counseling specialist."""
    text = "Saya mau bicara langsung sama customer service manusia."
    assert id_escalation_handler.is_escalation(text)
    resp = id_escalation_handler.get_escalation_response("colloquial")
    assert "Customer Service" in resp
    assert "dialihkan" in resp or "sambungkan" in resp


def test_language_preserving_unsupported_fallback():
    """
    Validates out-of-scope inquiries:
    Zero hallucination, strict Indonesian fallback, and customer service escalation offer.
    """
    session_id = "test_id_fallback"
    query = "Bagaimana resep cara membuat rendang sapi yang empuk?"
    res = id_dialog_manager.process_utterance(session_id, query)
    
    assert res["intent"] == "unsupported"
    assert res["language"] == "id"
    assert "Mohon maaf" in res["response"]
    assert "customer service" in res["response"].lower()
    assert res["citation"] is None


def test_q2_kb_retrieval_grounding_late_fee_policy():
    """Validates Q2 RAG retrieval of official Darwix Multifinance grace period and denda policy."""
    session_id = "test_id_kb_session"
    query = "Kalau saya telat bayar cicilan, ada late fee nggak?"
    res = id_dialog_manager.process_utterance(session_id, query)

    assert res["intent"] == "late_payment_fee"
    assert "3 hari" in res["response"].lower()  # 3-day grace period
    assert "0,5%" in res["response"]  # 0.5% per day denda
    assert res["citation"] is not None
    assert "Darwix ID KB" in res["citation"]


@pytest.mark.asyncio
async def test_full_indonesia_installment_flow_e2e():
    """
    Executes a complete multi-turn installment conversation:
    Greeting -> Late fee inquiry (Q2 KB) -> Objection on high denda -> Approved support path -> Neural TTS
    """
    session_id = "test_e2e_id_flow"
    agent = id_voice_agent

    # 1. Greeting
    start_res = agent.start_call(session_id, dialect_style="colloquial")
    assert "Darwix Multifinance" in start_res["text"]

    # 2. Turn 1: Caller asks about late fee with English finance code-switching
    t1 = await agent.handle_turn(
        session_id=session_id,
        user_utterance="Kalau saya telat bayar cicilan, ada late fee nggak?",
        synthesize_audio=False
    )
    assert t1["language"] == "id"
    assert t1["intent"] == "late_payment_fee"
    assert "0,5%" in t1["agent_response"]
    assert t1["citation"] is not None

    # 3. Turn 2: Caller raises sector-specific objection regarding high late fee
    t2 = await agent.handle_turn(
        session_id=session_id,
        user_utterance="Denda-nya terlalu tinggi kak, keberatan saya kalau segitu.",
        synthesize_audio=False
    )
    assert t2["intent"] == "payment_objection"
    assert t2["support_path_offered"] == "Denda Waiver Request"
    assert "waiver" in t2["agent_response"].lower() or "penghapusan denda" in t2["agent_response"].lower()

    # 4. Turn 3: Caller requests human customer service escalation
    t3 = await agent.handle_turn(
        session_id=session_id,
        user_utterance="Bisa tolong sambungkan ke agen customer service sekarang?",
        synthesize_audio=True
    )
    assert t3["escalated"] is True
    assert t3["audio_path"] is not None
    assert Path(t3["audio_path"]).exists()
