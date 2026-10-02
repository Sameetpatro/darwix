import pytest
import os
import asyncio
from pathlib import Path

from q3.philippines.locale import ph_locale, PhilippinesLocaleEngine
from q3.philippines.intent_detector import ph_intent_detector
from q3.philippines.qualification import ph_qualification_engine, PhilippinesInsuranceProfile
from q3.philippines.objections import ph_objection_handler
from q3.philippines.escalation import ph_escalation_handler
from q3.philippines.dialog_manager import ph_dialog_manager
from q3.philippines.agent import ph_voice_agent
from q3.philippines.tts import ph_tts_engine


def test_language_identification_english():
    """Validates pure English detection in financial context."""
    text = "I would like to apply for a life insurance policy with maximum coverage."
    res = ph_locale.detect_language(text)
    assert res.language == "en"
    assert res.code_switch is False


def test_language_identification_filipino():
    """Validates pure Filipino / Tagalog detection."""
    text = "Magandang araw po. Nais ko pong kumuha ng seguro para sa aking pamilya."
    res = ph_locale.detect_language(text)
    assert res.language == "fil"
    assert "po" in res.detected_markers
    assert res.code_switch is False


def test_language_identification_taglish_code_switching():
    """
    Validates the exact example from the prompt:
    'Gusto ko pong malaman kung magkano yung premium for this policy.'
    Must detect Taglish with code-switching and not translate to English.
    """
    text = "Gusto ko pong malaman kung magkano yung premium for this policy."
    res = ph_locale.detect_language(text)
    assert res.language == "taglish"
    assert res.code_switch is True
    assert "po" in res.detected_markers or "gusto" in res.detected_markers
    assert "premium" in res.insurance_terms_found
    assert "policy" in res.insurance_terms_found


def test_required_insurance_terminology_understanding():
    """
    Validates natural understanding of all 7 mandatory insurance terms:
    premium, policy, beneficiary, rider, lapse, coverage, bank referral.
    """
    sample_text = (
        "Magkano ang monthly premium para sa term policy na may ₱1M coverage? "
        "Pwede bang beneficiary ang anak ko at mag-add ng critical illness rider? "
        "Ano mangyayari kung mag-lapse ang account at may BDO bank referral ba kayo?"
    )
    terms = ph_locale.extract_insurance_terms(sample_text)
    expected_terms = ["premium", "policy", "beneficiary", "rider", "lapse", "coverage", "bank referral"]
    for t in expected_terms:
        assert t in terms, f"Mandatory terminology '{t}' missing from extraction"


def test_intent_detection_taglish_premium_information():
    """
    Validates intent classification on:
    'Gusto ko pong malaman kung magkano yung premium for this policy.'
    Expected:
    language = Taglish
    intent = premium_information
    sector = life_insurance
    """
    text = "Gusto ko pong malaman kung magkano yung premium for this policy."
    intent_res = ph_intent_detector.detect_intent(text)
    assert intent_res.language == "taglish"
    assert intent_res.code_switch is True
    assert intent_res.intent == "premium_information"
    assert intent_res.sector == "life_insurance"


def test_multi_slot_qualification_extraction():
    """Validates multi-slot extraction from natural conversational Taglish."""
    prof = PhilippinesInsuranceProfile()
    text = "34 anyos na po ako, gusto ko sana ng 1 million pesos coverage at BDO depositor po ako."
    updated, extracted = ph_qualification_engine.extract_slots(text, prof)
    
    assert updated.age == 34
    assert updated.target_coverage == 1000000.0
    assert updated.bank_partner == "BDO Unibank"
    assert "monthly_budget" in updated.get_missing_fields()
    
    # Prompt asks only for missing budget
    next_q = ph_qualification_engine.get_next_question(updated, "taglish")
    assert "monthly budget" in next_q.lower() or "budget" in next_q.lower()


def test_objection_handling_taglish_and_english():
    """Validates cultural objection handling in both Taglish and English."""
    # Taglish objection
    taglish_obj = "Masyadong mahal yung premium ninyo, hindi ko afford."
    assert ph_objection_handler.is_objection(taglish_obj)
    resp_taglish = ph_objection_handler.handle_objection(taglish_obj, "taglish")
    assert "1,500" in resp_taglish or "50" in resp_taglish
    assert "po" in resp_taglish

    # English objection
    en_obj = "The premium is too expensive for my budget right now."
    assert ph_objection_handler.is_objection(en_obj)
    resp_en = ph_objection_handler.handle_objection(en_obj, "en")
    assert "1,500" in resp_en or "50" in resp_en
    assert "customize" in resp_en.lower()


def test_human_escalation_warm_transfer():
    """Validates human escalation detection in Filipino, Taglish, and English."""
    fil_req = "Gusto ko pong makausap ang live financial advisor o manager ninyo."
    assert ph_escalation_handler.is_escalation(fil_req)
    fil_resp = ph_escalation_handler.get_escalation_response("fil")
    assert "ikokonekta" in fil_resp.lower() or "financial advisor" in fil_resp.lower()

    en_req = "Can I speak to a human representative please?"
    assert ph_escalation_handler.is_escalation(en_req)
    en_resp = ph_escalation_handler.get_escalation_response("en")
    assert "connect" in en_resp.lower() and "financial advisor" in en_resp.lower()


def test_language_preserving_unsupported_fallback():
    """
    Validates that unsupported inquiries outside the KB:
    1. Do not hallucinate.
    2. Preserve the caller's language (Taglish caller receives Taglish fallback; English receives English).
    3. Offer human assistance.
    """
    session_id = "test_fallback_session"
    
    # 1. Taglish out-of-scope query
    taglish_query = "Paano po ba mag-bake ng chocolate chip cookies sa bahay?"
    res_taglish = ph_dialog_manager.process_utterance(session_id, taglish_query)
    assert res_taglish["intent"] == "unsupported"
    assert res_taglish["language"] == "taglish"
    assert "Wala po akong maaasahang impormasyon" in res_taglish["response"]
    assert "financial advisor" in res_taglish["response"].lower()

    # 2. English out-of-scope query
    en_query = "What is the current price of Bitcoin on Binance crypto exchange?"
    res_en = ph_dialog_manager.process_utterance(session_id, en_query)
    assert res_en["intent"] == "unsupported"
    assert res_en["language"] == "en"
    assert "I don't have reliable information" in res_en["response"]
    assert "financial advisor" in res_en["response"].lower()


def test_q2_kb_retrieval_grounding_lapse_policy():
    """Validates grounded retrieval from Q2 KB for Philippines policy lapse and grace period."""
    session_id = "test_kb_lapse_session"
    query = "Ano po ang mangyayari kung hindi ako makabayad sa due date? May grace period po ba?"
    res = ph_dialog_manager.process_utterance(session_id, query)
    
    assert res["intent"] in ["lapse_inquiry", "premium_information"]
    assert "31" in res["response"]  # 31-day grace period
    assert res["citation"] is not None
    assert "Darwix PH KB" in res["citation"]


def test_q2_kb_retrieval_bancassurance_perks():
    """Validates grounded retrieval from Q2 KB for Bancassurance partner perks."""
    session_id = "test_kb_banc_session"
    query = "Anong perks kung may BDO o BPI account ako under bancassurance?"
    res = ph_dialog_manager.process_utterance(session_id, query)
    
    assert res["citation"] is not None
    assert "3" in res["response"] or "rebate" in res["response"].lower() or "bdo" in res["response"].lower()


@pytest.mark.asyncio
async def test_full_conversational_flow_e2e():
    """
    Executes a complete multi-turn conversation in Taglish:
    Greeting -> Inquiry -> Qualification -> Objection -> Resolution -> Recommendation -> Audio TTS
    """
    session_id = "test_e2e_ph_flow"
    agent = ph_voice_agent

    # 1. Greeting
    start_res = agent.start_call(session_id, language="taglish")
    assert "Magandang araw" in start_res["text"]

    # 2. Turn 1: Caller asks about policy and coverage
    t1 = await agent.handle_turn(
        session_id=session_id,
        user_utterance="Gusto ko po sanang magtanong tungkol sa life insurance para sa proteksyon ng pamilya ko.",
        synthesize_audio=False
    )
    assert t1["language"] == "taglish"

    # 3. Turn 2: Caller provides age and coverage requirement
    t2 = await agent.handle_turn(
        session_id=session_id,
        user_utterance="Ako po ay 30 anyos, kailangan ko ng 1 million pesos coverage para sa asawa at anak ko.",
        synthesize_audio=False
    )
    assert t2["qualification_profile"]["age"] == 30
    assert t2["qualification_profile"]["target_coverage"] == 1000000.0

    # 4. Turn 3: Caller raises budget objection
    t3 = await agent.handle_turn(
        session_id=session_id,
        user_utterance="Medyo mahal yata ang monthly premium niyan, baka hindi kayanin.",
        synthesize_audio=False
    )
    assert t3["intent"] == "objection"
    assert "1,500" in t3["agent_response"] or "50" in t3["agent_response"]

    # 5. Turn 4: Caller agrees on budget and mentions partner bank
    t4 = await agent.handle_turn(
        session_id=session_id,
        user_utterance="Sige po, pasok ang 2,000 kada buwan sa BDO account ko.",
        synthesize_audio=True
    )
    assert t4["qualification_profile"]["monthly_budget"] == 2000.0
    assert "BDO" in t4["qualification_profile"]["bank_partner"]
    assert t4["completed"] is True
    assert t4["audio_path"] is not None
    assert Path(t4["audio_path"]).exists()
