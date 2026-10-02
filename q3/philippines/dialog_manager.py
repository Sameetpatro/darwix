import time
import re
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from q3.philippines.locale import ph_locale, LanguageDetectionResult
from q3.philippines.intent_detector import ph_intent_detector, PhilippinesIntentResult
from q3.philippines.qualification import ph_qualification_engine, PhilippinesInsuranceProfile
from q3.philippines.objections import ph_objection_handler
from q3.philippines.escalation import ph_escalation_handler
from q2.retrieval.hybrid_search import HybridSearchEngine
from app.logging_config import logger


class PhilippinesConversationSession(BaseModel):
    """Tracks state and history for a Philippines life insurance caller."""
    session_id: str
    language: str = "taglish"  # 'taglish', 'fil', or 'en'
    profile: PhilippinesInsuranceProfile = Field(default_factory=PhilippinesInsuranceProfile)
    turns: List[Dict[str, Any]] = Field(default_factory=list)
    escalated: bool = False
    completed: bool = False
    created_at: float = Field(default_factory=time.time)


class PhilippinesDialogManager:
    """
    Orchestrates turn-by-turn conversation for Philippines Life Insurance / Bancassurance.
    Preserves natural language and code-switching without translation.
    """

    def __init__(self, hybrid_engine: Optional[HybridSearchEngine] = None):
        self.hybrid_engine = hybrid_engine or HybridSearchEngine()
        self.sessions: Dict[str, PhilippinesConversationSession] = {}

    def get_or_create_session(self, session_id: str) -> PhilippinesConversationSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = PhilippinesConversationSession(session_id=session_id)
        return self.sessions[session_id]

    def greet(self, session_id: str, language: str = "taglish") -> str:
        """Returns culturally warm initial greeting."""
        session = self.get_or_create_session(session_id)
        session.language = language

        if language == "fil":
            greeting = (
                "Magandang araw po! Maligayang pagdating sa Darwix Life Bancassurance. "
                "Ako po si Vani, ang inyong digital insurance specialist. "
                "Paano ko po kayo matutulungan sa araw na ito?"
            )
        elif language == "en":
            greeting = (
                "Good day! Welcome to Darwix Life Bancassurance. "
                "I am Vani, your digital life insurance specialist. "
                "How may I assist you with your family protection and bancassurance needs today?"
            )
        else: # taglish
            greeting = (
                "Magandang araw po! Welcome sa Darwix Life Bancassurance. "
                "Ako po si Vani, ang inyong insurance specialist. "
                "Nandito po ako para tulungan kayo sa life protection at bancassurance plans. "
                "Paano ko po kayo matutulungan today?"
            )

        session.turns.append({
            "speaker": "agent",
            "text": greeting,
            "intent": "greeting",
            "language": language,
            "timestamp": time.time()
        })
        return greeting

    def process_utterance(self, session_id: str, utterance: str) -> Dict[str, Any]:
        """
        Processes a customer utterance in English, Filipino, or Taglish.
        Returns:
            {
                "response": str,
                "language": str,
                "intent": str,
                "escalated": bool,
                "completed": bool,
                "evidence": List[Dict],
                "citation": Optional[str],
                "missing_slots": List[str]
            }
        """
        session = self.get_or_create_session(session_id)
        
        # 1. Detect language and intent
        intent_res = ph_intent_detector.detect_intent(utterance)
        detected_lang = intent_res.language
        session.language = detected_lang  # adaptively align to caller's language

        logger.info(
            f"[PH-DIALOG] Session '{session_id}' | Lang: {detected_lang} | Intent: {intent_res.intent} | Utterance: '{utterance}'"
        )

        # 2. Check for human escalation
        if intent_res.intent == "human_escalation" or ph_escalation_handler.is_escalation(utterance):
            session.escalated = True
            resp = ph_escalation_handler.get_escalation_response(detected_lang)
            session.turns.append({"speaker": "user", "text": utterance, "intent": "human_escalation"})
            session.turns.append({"speaker": "agent", "text": resp, "intent": "human_escalation"})
            return {
                "response": resp,
                "language": detected_lang,
                "intent": "human_escalation",
                "escalated": True,
                "completed": False,
                "evidence": [],
                "citation": None,
                "missing_slots": session.profile.get_missing_fields()
            }

        # 3. Check for objection handling
        if intent_res.intent == "objection" or ph_objection_handler.is_objection(utterance):
            resp = ph_objection_handler.handle_objection(utterance, detected_lang)
            session.turns.append({"speaker": "user", "text": utterance, "intent": "objection"})
            session.turns.append({"speaker": "agent", "text": resp, "intent": "objection"})
            return {
                "response": resp,
                "language": detected_lang,
                "intent": "objection",
                "escalated": False,
                "completed": False,
                "evidence": [],
                "citation": None,
                "missing_slots": session.profile.get_missing_fields()
            }

        # 4. Check for out-of-scope / unsupported question
        if intent_res.intent == "unsupported":
            resp = self._get_unsupported_fallback(detected_lang)
            session.turns.append({"speaker": "user", "text": utterance, "intent": "unsupported"})
            session.turns.append({"speaker": "agent", "text": resp, "intent": "unsupported"})
            return {
                "response": resp,
                "language": detected_lang,
                "intent": "unsupported",
                "escalated": False,
                "completed": False,
                "evidence": [],
                "citation": None,
                "missing_slots": session.profile.get_missing_fields()
            }

        # 5. Extract qualification entities if user provided any
        updated_profile, extracted_this_turn = ph_qualification_engine.extract_slots(utterance, session.profile)
        session.profile = updated_profile

        # If qualification is now complete, prioritize proposal summary
        if extracted_this_turn and session.profile.is_complete():
            session.completed = True
            resp = ph_qualification_engine.get_qualification_summary(session.profile, detected_lang)
            session.turns.append({"speaker": "user", "text": utterance, "intent": "qualification"})
            session.turns.append({"speaker": "agent", "text": resp, "intent": "qualification"})
            return {
                "response": resp,
                "language": detected_lang,
                "intent": "qualification",
                "escalated": False,
                "completed": True,
                "evidence": [],
                "citation": None,
                "missing_slots": []
            }

        # 6. Check for Domain Knowledge Questions (e.g. lapse, premium, rider, beneficiary, bancassurance)
        kb_intents = {
            "lapse_inquiry", "premium_information", "rider_inquiry",
            "beneficiary_inquiry", "bancassurance_inquiry", "coverage_inquiry", "policy_inquiry"
        }

        evidence_list = []
        citation_str = None

        is_question = bool(re.search(r"\?|\b(?:ano|paano|magkano|bakit|kailan|how|what|why|meron\s+ba|may\s+perks|pwede\s+ba)\b", utterance.lower()))

        if (intent_res.intent in kb_intents or any(t in utterance.lower() for t in ["lapse", "grace period", "rider", "critical illness", "beneficiary", "prepayment"])) and (is_question or not extracted_this_turn):
            # Search Q2 Knowledge Base
            search_hits = self.hybrid_engine.search(query=utterance, top_k=2)
            if search_hits and (search_hits[0].dense_score > 0.55 or search_hits[0].sparse_score > 0.0):
                top_hit = search_hits[0]
                citation_str = f"Darwix PH KB: {top_hit.chunk.source} ({top_hit.chunk.title})"
                evidence_list = [
                    {
                        "title": top_hit.chunk.title,
                        "content": top_hit.chunk.content,
                        "citation": citation_str,
                        "score": top_hit.fused_score
                    }
                ]
                # Format localized grounded response based on top hit content
                resp = self._format_kb_response(utterance, top_hit.chunk.content, detected_lang, intent_res.intent)
                
                # If qualification is in progress, gently append missing slot prompt
                missing = session.profile.get_missing_fields()
                if missing and len(missing) < 5:
                    next_q = ph_qualification_engine.get_next_question(session.profile, detected_lang)
                    resp = f"{resp}\n\nBy the way po, {next_q.lower()}" if detected_lang == "taglish" else f"{resp}\n\n{next_q}"

                session.turns.append({"speaker": "user", "text": utterance, "intent": intent_res.intent})
                session.turns.append({"speaker": "agent", "text": resp, "intent": intent_res.intent, "citation": citation_str})
                return {
                    "response": resp,
                    "language": detected_lang,
                    "intent": intent_res.intent,
                    "escalated": False,
                    "completed": False,
                    "evidence": evidence_list,
                    "citation": citation_str,
                    "missing_slots": session.profile.get_missing_fields()
                }

        # 7. Qualification progression flow
        if extracted_this_turn or intent_res.intent == "qualification_answer" or intent_res.intent == "quote_inquiry":
            if session.profile.is_complete():
                session.completed = True
                resp = ph_qualification_engine.get_qualification_summary(session.profile, detected_lang)
            else:
                resp = ph_qualification_engine.get_next_question(session.profile, detected_lang)

            session.turns.append({"speaker": "user", "text": utterance, "intent": "qualification"})
            session.turns.append({"speaker": "agent", "text": resp, "intent": "qualification"})
            return {
                "response": resp,
                "language": detected_lang,
                "intent": "qualification",
                "escalated": False,
                "completed": session.completed,
                "evidence": [],
                "citation": None,
                "missing_slots": session.profile.get_missing_fields()
            }

        # 8. Fallback to next qualification question or friendly clarification
        if not session.profile.is_complete():
            resp = ph_qualification_engine.get_next_question(session.profile, detected_lang)
        else:
            resp = ph_qualification_engine.get_qualification_summary(session.profile, detected_lang)

        session.turns.append({"speaker": "user", "text": utterance, "intent": "general"})
        session.turns.append({"speaker": "agent", "text": resp, "intent": "general"})
        return {
            "response": resp,
            "language": detected_lang,
            "intent": "general",
            "escalated": False,
            "completed": session.completed,
            "evidence": [],
            "citation": None,
            "missing_slots": session.profile.get_missing_fields()
        }

    def _get_unsupported_fallback(self, language: str) -> str:
        """Language-preserving strict fallback for out-of-scope inquiries."""
        if language == "fil":
            return (
                "Wala po akong hawak na maaasahang impormasyon tungkol diyan sa kasalukuyan. "
                "Maaari ko po kayong ikonekta sa aming lisensyadong Financial Advisor kung inyong nais."
            )
        elif language == "en":
            return (
                "I don't have reliable information about that at the moment. "
                "I can connect you with a licensed Financial Advisor if you'd like."
            )
        else: # taglish
            return (
                "Wala po akong maaasahang impormasyon tungkol diyan sa ngayon. "
                "Pwede po kitang ikonekta sa isang licensed Financial Advisor kung gusto niyo po."
            )

    def _format_kb_response(self, query: str, content: str, language: str, intent: str) -> str:
        """Synthesizes clean conversational response from retrieved evidence in caller's language."""
        clean_content = content.replace("##", "").replace("**", "").strip()

        # Specific intent synthesis
        if intent == "lapse_inquiry":
            if language == "fil":
                return (
                    "Batay sa aming patakaran, mayroon po kayong 31-day grace period sa bawat due date kung saan aktibo pa rin ang inyong seguro. "
                    "Kung lumagpas po sa 31 araw at mag-lapse ang polisa, maaari pa rin po itong i-reinstate sa loob ng tatlong (3) taon "
                    "sa pamamagitan ng pagsusumite ng health declaration at pagbabayad ng overdue premiums."
                )
            elif language == "en":
                return (
                    "According to our Darwix policy rules, all policies include a statutory 31-day grace period where your coverage remains 100% active. "
                    "If a policy lapses past the grace period, it can be reinstated within three (3) years upon submission of a health declaration "
                    "and settlement of overdue premiums with interest."
                )
            else: # taglish
                return (
                    "Ayon po sa Darwix policy guidelines, may 31-day grace period po tayo kapag may na-miss na due date, at nananatiling 100% active ang inyong coverage. "
                    "Kung mag-lapse man po, pwede niyo pa po itong ma-reinstate within 3 years sa pamamagitan ng simpleng health declaration at pagbayad ng missed premiums."
                )

        if intent == "rider_inquiry":
            if language == "fil":
                return (
                    "Maaari po kayong magdagdag ng mga kapaki-pakinabang na riders tulad ng Critical Illness Benefit (CIB) na sumasakop sa 36 na malulubhang sakit "
                    "tulad ng cancer at stroke, Accidental Death Benefit, at Waiver of Premium kung sakaling magkaroon ng kapansanan."
                )
            elif language == "en":
                return (
                    "You can attach optional supplemental riders to your policy, including the Critical Illness Benefit covering 36 illnesses like cancer and stroke, "
                    "Accidental Death & Dismemberment, and Waiver of Premium upon total disability."
                )
            else: # taglish
                return (
                    "Pwede po kayong mag-add ng optional riders tulad ng Critical Illness Benefit (covering 36 major illnesses tulad ng cancer at stroke), "
                    "Accidental Death Benefit, at Waiver of Premium para po kung may mangyaring disability, libre na ang mga susunod na hulog."
                )

        if intent == "bancassurance_inquiry":
            if language == "fil":
                return (
                    "Dahil po sa ating Bancassurance partnership sa BDO, BPI, Metrobank, at Security Bank, "
                    "makakakuha po kayo ng express non-medical underwriting hanggang ₱3 Million coverage at 5% auto-debit rebate sa unang taon."
                )
            elif language == "en":
                return (
                    "Through our Bancassurance partnerships with BDO, BPI, Metrobank, and Security Bank, "
                    "account holders qualify for fast-track non-medical underwriting up to ₱3 Million face amount and a 5% first-year auto-debit rebate."
                )
            else: # taglish
                return (
                    "Dahil po sa ating Bancassurance partnership sa BDO, BPI, Metrobank, at Security Bank, "
                    "may privilege po kayo na express non-medical approval up to ₱3 Million face amount, plus 5% premium rebate sa auto-debit enrollment!"
                )

        # General extraction fallback
        first_few_lines = "\n".join(clean_content.split("\n")[:3])
        if language == "fil":
            return f"Ayon po sa aming patakaran sa seguro:\n{first_few_lines}"
        elif language == "en":
            return f"According to our official insurance guidelines:\n{first_few_lines}"
        else:
            return f"Ayon po sa aming official guidelines:\n{first_few_lines}"


ph_dialog_manager = PhilippinesDialogManager()
