import time
import asyncio
from typing import Dict, Any, Optional
from app.config import settings
from app.logging_config import logger
from app.state import session_manager, CallSession, LatencyBreakdown
from app.llm.deepseek import deepseek_client, clean_text_for_speech
from app.tts.edge_tts_engine import tts_engine
from app.asr.asr_handler import asr_handler
from app.qualification.dialog_manager import dialog_manager
from q3.indonesia.locale import id_locale
from q3.indonesia.intent_detector import id_intent_detector
from q3.indonesia.dialog_manager import id_dialog_manager
from q3.philippines.locale import ph_locale
from q3.philippines.intent_detector import ph_intent_detector
from q3.philippines.dialog_manager import ph_dialog_manager
from q4.conversation.buffer import ConversationTurn
from q4.conversation.state import LiveCallState
from q4.signals.engine import signal_engine
from q4.nudge.engine import nudge_engine
from q4.delivery.websocket import ws_delivery_manager
from q4.api.router import active_call_states

import re

INITIAL_AGENT_GREETING = "Hello! Welcome to Darwix. I'm Vani, your AI voice specialist. How can I assist you with your loan, installment, or financing needs today?"

ID_WORDS = {
    "saya", "aku", "anda", "kamu", "kami", "kita", "ini", "itu", "yang", "dan", "di", "ke", "dari",
    "ada", "tidak", "nggak", "gak", "tak", "bisa", "mau", "akan", "sudah", "udah", "belum", "lagi",
    "kalo", "kalau", "apakah", "apa", "siapa", "bagaimana", "gimana", "kenapa", "mengapa", "kapan",
    "berapa", "dengan", "untuk", "pada", "oleh", "karena", "tapi", "tetapi", "juga", "hanya", "cuma",
    "saja", "boleh", "harus", "tolong", "mohon", "terima", "kasih", "makasih", "halo", "selamat",
    "kak", "bang", "mas", "mbak", "pak", "bu", "dong", "nih", "deh", "sih", "ya", "iya", "banget",
    "bener", "rek", "monggo", "nggih", "teh", "kumaha", "lusa", "gajian", "telat", "bisa"
}

PH_WORDS = {
    "po", "opo", "ako", "ikaw", "ka", "kami", "tayo", "kayo", "sila", "ko", "mo", "niya", "namin",
    "ninyo", "nila", "ito", "iyan", "iyon", "ang", "ng", "sa", "kay", "kina", "mga", "ay", "at",
    "kung", "kapag", "dahil", "para", "pero", "kasi", "kaya", "naman", "ba", "na", "pa", "din",
    "rin", "lang", "daw", "raw", "sana", "pala", "talaga", "hindi", "di", "oo", "wala", "meron",
    "magkano", "ano", "paano", "kailan", "saan", "bakit", "kumusta", "salamat", "kuya", "ate"
}

EN_WORDS = {
    "the", "is", "are", "am", "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "can", "could", "will", "would", "shall", "should", "may", "might", "must",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "my", "your",
    "his", "her", "its", "our", "their", "this", "that", "these", "those", "in", "on", "at", "to",
    "for", "from", "with", "by", "about", "of", "off", "over", "under", "then", "here", "there",
    "when", "where", "why", "how", "what", "if", "or", "and", "but", "so", "because", "as",
    "hello", "hi", "hey", "please", "thank", "thanks", "yes", "no", "want", "need", "like",
    "tell", "explain", "help", "days", "late", "pay", "payment", "fee", "penalty", "miss",
    "who", "which", "whom", "whose", "good", "morning", "afternoon", "evening"
}

ID_MULTIFINANCE_TERMS = [
    "cicilan", "denda", "angsuran", "tenor", "uang muka", "jatuh tempo",
    "pembiayaan", "motorcycle installment", "car financing", "vehicle financing", "vehicle loan",
    "bpkb", "slik", "ojk", "keringanan", "potongan", "terlalu tinggi",
    "kemahalan", "janji bayar", "pelunasan dipercepat", "multifinance", "ptp"
]

PH_INSURANCE_TERMS = [
    "life insurance", "insurance policy", "policy", "premium", "beneficiary", "beneficiaries",
    "rider", "riders", "lapse", "polisa", "bancassurance", "bdo", "bpi", "metrobank",
    "critical illness", "accidental death", "auto-debit", "bank referral", "insurance"
]


def detect_speech_language(text: str) -> str:
    """
    Accurately classifies the spoken language of the utterance into 'en', 'id', or 'taglish',
    regardless of localized financial loanwords (e.g. 'denda', 'cicilan').
    """
    tokens = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    if not tokens:
        return "en"

    id_score = sum(1 for t in tokens if t in ID_WORDS)
    ph_score = sum(1 for t in tokens if t in PH_WORDS)
    en_score = sum(1 for t in tokens if t in EN_WORDS)

    if ph_score >= 1 and ph_score >= id_score and ph_score >= en_score:
        return "taglish"
    if id_score > en_score and id_score >= ph_score:
        return "id"
    if en_score > 0:
        return "en"
    if id_score > 0:
        return "id"
    if ph_score > 0:
        return "taglish"
    return "en"


class VoicePipeline:
    def __init__(self):
        self.session_manager = session_manager
        self.llm = deepseek_client
        self.tts = tts_engine
        self.asr = asr_handler
        self.dialog_manager = dialog_manager

    async def initialize_call(self, call_id: str, caller_id: str = "web_user") -> Dict[str, Any]:
        """
        Starts a new call session, generates the opening agent greeting, and synthesizes audio.
        """
        start_time = time.perf_counter()
        logger.info("[PIPELINE] Initializing call %s for caller %s", call_id, caller_id)

        session = self.session_manager.create_session(call_id=call_id, caller_id=caller_id)

        # 1. Opening greeting
        greeting_text = INITIAL_AGENT_GREETING

        # 2. Synthesize audio
        audio_url, audio_path, tts_ms = await self.tts.synthesize(
            text=greeting_text,
            call_id=call_id,
            turn_id=1,
        )

        total_ms = (time.perf_counter() - start_time) * 1000
        latencies = LatencyBreakdown(
            asr_ms=0.0,
            llm_ms=0.0,
            tts_ms=round(tts_ms, 1),
            total_roundtrip_ms=round(total_ms, 1),
        )

        # 3. Record opening turn
        turn = session.add_turn(
            speaker="agent",
            text=greeting_text,
            audio_url=audio_url,
            audio_path=audio_path,
            latencies=latencies,
        )

        # 4. Bridge to Q4 Live Copilot Pipeline
        q4_state = LiveCallState(call_id=call_id)
        active_call_states[call_id] = q4_state
        await ws_delivery_manager.broadcast_event("call_started", {
            "call_id": call_id,
            "scenario": "Live Call",
            "turns_total": 0,
            "status": "active"
        })
        q4_opening_turn = ConversationTurn(
            turn_id="turn_001",
            call_id=call_id,
            speaker="agent",
            text=greeting_text,
            start_timestamp=start_time,
            end_timestamp=time.perf_counter(),
            confidence=1.0,
            turn_index=1,
        )
        q4_state.add_turn(q4_opening_turn)
        await ws_delivery_manager.broadcast_event("turn_finalized", {
            "turn_id": q4_opening_turn.turn_id,
            "speaker": q4_opening_turn.speaker,
            "text": q4_opening_turn.text,
            "confidence": q4_opening_turn.confidence,
            "stage": q4_state.stage
        })

        return {
            "call_id": call_id,
            "status": session.status,
            "turn_id": turn.turn_id,
            "agent_text": greeting_text,
            "audio_url": audio_url,
            "qualification": session.loan_application.get_summary_dict(),
            "latencies": latencies.model_dump(),
        }

    async def process_user_speech(
        self,
        call_id: str,
        user_text: str,
        client_asr_duration_ms: Optional[float] = None,
        confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Executes the voice conversational loop with Business Loan Qualification:
        Customer Speech (ASR) -> Qualification Dialog Manager -> State / LLM -> TTS -> Audio Playback
        """
        overall_start = time.perf_counter()
        session = self.session_manager.get_session(call_id)
        if not session:
            logger.warning("[PIPELINE] Session %s not found. Creating auto session.", call_id)
            session = self.session_manager.create_session(call_id=call_id)

        # Step 1: Process ASR input
        asr_result = self.asr.process_transcript(
            text=user_text,
            client_duration_ms=client_asr_duration_ms,
            confidence=confidence,
        )
        clean_user_text = asr_result["text"]
        asr_ms = asr_result["asr_latency_ms"]

        # Step 2: Record Customer Turn
        session.add_turn(
            speaker="customer",
            text=clean_user_text,
            latencies=LatencyBreakdown(asr_ms=asr_ms, total_roundtrip_ms=asr_ms),
        )

        # Q4 Real-Time Copilot Ingestion & Signal Extraction
        q4_state = active_call_states.get(call_id)
        if not q4_state:
            q4_state = LiveCallState(call_id=call_id)
            active_call_states[call_id] = q4_state

        q4_cust_turn = ConversationTurn(
            turn_id=f"turn_{len(session.turns):03d}",
            call_id=call_id,
            speaker="customer",
            text=clean_user_text,
            start_timestamp=overall_start,
            end_timestamp=time.perf_counter(),
            confidence=confidence or 0.95,
            asr_latency_ms=asr_ms,
            turn_index=len(session.turns),
        )
        q4_state.add_turn(q4_cust_turn)
        await ws_delivery_manager.broadcast_event("turn_finalized", {
            "turn_id": q4_cust_turn.turn_id,
            "speaker": q4_cust_turn.speaker,
            "text": q4_cust_turn.text,
            "confidence": q4_cust_turn.confidence,
            "stage": q4_state.stage,
        })

        # Run Q4 Signal Detection (L2) & Nudge Engine (L3) -> WebSocket (L4)
        signals = signal_engine.process_turn(q4_cust_turn, q4_state)
        for sig in signals:
            q4_state.add_signal(sig)
            await ws_delivery_manager.broadcast_event("signal_detected", sig.model_dump())
            nudge = await nudge_engine.process_signal(sig, q4_state, use_deepseek=False)
            if nudge:
                l4_ms = await ws_delivery_manager.broadcast_nudge(nudge)
                l1_ms = asr_ms
                l2_ms = sig.detection_latency_ms
                l3_ms = nudge.generation_latency_ms
                l_total_ms = round(l1_ms + l2_ms + l3_ms + l4_ms, 2)
                await ws_delivery_manager.broadcast_event("latency_sample", {
                    "signal_id": sig.signal_id,
                    "nudge_id": nudge.nudge_id,
                    "type": nudge.type,
                    "L1_asr_ms": l1_ms,
                    "L2_signal_ms": l2_ms,
                    "L3_nudge_ms": l3_ms,
                    "L4_delivery_ms": l4_ms,
                    "L_total_ms": l_total_ms,
                })
            else:
                await ws_delivery_manager.broadcast_event("signal_suppressed", {
                    "signal_id": sig.signal_id,
                    "type": sig.type,
                    "confidence": sig.confidence,
                    "reason": "Suppressed by Nudge Engine",
                })

        # Step 3: Unified Multilingual & Intent-Aware Dialogue Engine
        llm_start = time.perf_counter()
        lower_text = clean_user_text.lower()

        # 3a. Accurately detect caller's input language
        input_lang = detect_speech_language(clean_user_text)

        # 3b. Check active domain in session context
        active_domain = session.metadata.get("active_domain")

        # 3c. Explicit domain switch triggers
        if any(w in lower_text for w in ["switch to commercial loan", "us business loan", "switch to business loan", "commercial lending", "commercial loan in the us"]):
            active_domain = "us_commercial_loan"
        elif any(w in lower_text for w in ["switch to indonesia", "pindah ke indonesia", "darwix multifinance", "motorcycle financing"]):
            active_domain = "indonesia_multifinance"
        elif any(w in lower_text for w in ["switch to philippines", "switch to insurance", "darwix life insurance", "darwix life bancassurance"]):
            active_domain = "philippines_insurance"

        # 3d. Domain & Context Resolution
        id_hits = sum(1 for term in ID_MULTIFINANCE_TERMS if term in lower_text)
        ph_hits = sum(1 for term in PH_INSURANCE_TERMS if term in lower_text)

        if active_domain is None:
            # First turn: establish domain based on intent and language
            if input_lang == "id":
                active_domain = "indonesia_multifinance"
            elif input_lang in ("taglish", "filipino"):
                active_domain = "philippines_insurance"
            elif ph_hits > id_hits and ph_hits > 0:
                active_domain = "philippines_insurance"
            elif id_hits > ph_hits and id_hits > 0:
                active_domain = "indonesia_multifinance"
            else:
                # User started in English: talk about the main English thing (US Commercial Loan qualification)
                active_domain = "us_commercial_loan"
        else:
            # Domain already active: PERSIST CONTEXT!
            # If user was in us_commercial_loan and asks about consumer finance or insurance, capture intent and switch
            if active_domain == "us_commercial_loan":
                if ph_hits > id_hits and ph_hits > 0:
                    active_domain = "philippines_insurance"
                elif id_hits > ph_hits and id_hits > 0:
                    active_domain = "indonesia_multifinance"

        session.metadata["active_domain"] = active_domain
        kb_citation = None

        # 3e. Route turn while strictly ensuring Response Language == Input Language
        if active_domain == "indonesia_multifinance":
            # Response language MUST match caller's input language
            resp_lang = "en" if input_lang == "en" else "id"
            logger.info("[PIPELINE] Indonesian Multifinance Domain (Input Lang: %s -> Response Lang: %s)", input_lang, resp_lang)

            id_res = id_dialog_manager.process_utterance(
                session_id=call_id,
                utterance=clean_user_text,
                language=resp_lang,
            )
            target_reply = id_res["response"]
            kb_citation = id_res.get("citation")
            selected_voice = "en-US-JennyNeural" if resp_lang == "en" else "id-ID-GadisNeural"
            detected_language = resp_lang
            provider_used = f"indonesia_multifinance_engine ({id_res.get('intent', 'multifinance')})"
            dialog_meta = {
                "action": "indonesia_dialog_turn",
                "intent": id_res.get("intent"),
                "dialect_style": id_res.get("dialect_style"),
                "escalated": id_res.get("escalated", False),
                "support_path_offered": id_res.get("support_path_offered"),
                "kb_citation": kb_citation,
            }
            if id_res.get("escalated"):
                session.status = "escalated"

        elif active_domain == "philippines_insurance":
            # Response language MUST match caller's input language
            resp_lang = "en" if input_lang == "en" else "taglish"
            logger.info("[PIPELINE] Philippines Insurance Domain (Input Lang: %s -> Response Lang: %s)", input_lang, resp_lang)

            ph_res = ph_dialog_manager.process_utterance(
                session_id=call_id,
                utterance=clean_user_text,
                language=resp_lang,
            )
            target_reply = ph_res["response"]
            kb_citation = ph_res.get("citation")
            selected_voice = "en-PH-RosaNeural" if resp_lang == "en" else "fil-PH-BlessicaNeural"
            detected_language = resp_lang
            provider_used = f"philippines_insurance_engine ({ph_res.get('intent', 'insurance')})"
            dialog_meta = {
                "action": "philippines_dialog_turn",
                "intent": ph_res.get("intent"),
                "escalated": ph_res.get("escalated", False),
                "kb_citation": kb_citation,
            }
            if ph_res.get("escalated"):
                session.status = "escalated"

        else:
            # Talk about the main English thing: US Commercial Loan Underwriting Engine (Q1)
            logger.info("[PIPELINE] Routing to US Commercial Loan Underwriting Engine (Main English Flow)")
            target_reply, dialog_meta = self.dialog_manager.process_turn(
                app=session.loan_application,
                user_utterance=clean_user_text,
                turn_number=len(session.turns),
            )
            selected_voice = settings.tts_voice
            detected_language = "en"
            provider_used = "qualification_dialog_engine"
            kb_citation = dialog_meta.get("kb_citation")
            if dialog_meta.get("action") == "escalate":
                session.status = "escalated"
            elif dialog_meta.get("action") == "underwriting_decision":
                dec_status = dialog_meta.get("decision", {}).get("status")
                if dec_status:
                    session.status = f"underwriting_{dec_status.lower()}"

        agent_reply_text = clean_text_for_speech(target_reply)
        llm_ms = (time.perf_counter() - llm_start) * 1000

        # Step 4: Synthesize TTS Audio in the detected language's neural voice
        turn_num = len(session.turns) + 1
        audio_url, audio_path, tts_ms = await self.tts.synthesize(
            text=agent_reply_text,
            call_id=call_id,
            turn_id=turn_num,
            voice=selected_voice,
        )

        # Step 5: Compute Total Latency & Record Agent Turn
        overall_total_ms = (time.perf_counter() - overall_start) * 1000
        latencies = LatencyBreakdown(
            asr_ms=round(asr_ms, 1),
            llm_ms=round(llm_ms, 1),
            tts_ms=round(tts_ms, 1),
            total_roundtrip_ms=round(overall_total_ms, 1),
        )

        agent_turn = session.add_turn(
            speaker="agent",
            text=agent_reply_text,
            audio_url=audio_url,
            audio_path=audio_path,
            latencies=latencies,
            kb_citation=kb_citation,
        )

        # Ingest agent turn into Q4 & run compliance checks
        q4_agent_turn = ConversationTurn(
            turn_id=f"turn_{agent_turn.turn_id:03d}",
            call_id=call_id,
            speaker="agent",
            text=agent_reply_text,
            start_timestamp=llm_start,
            end_timestamp=time.perf_counter(),
            confidence=1.0,
            turn_index=agent_turn.turn_id,
        )
        q4_state.add_turn(q4_agent_turn)
        await ws_delivery_manager.broadcast_event("turn_finalized", {
            "turn_id": q4_agent_turn.turn_id,
            "speaker": q4_agent_turn.speaker,
            "text": q4_agent_turn.text,
            "confidence": q4_agent_turn.confidence,
            "stage": q4_state.stage,
        })
        agent_signals = signal_engine.process_turn(q4_agent_turn, q4_state)
        for sig in agent_signals:
            q4_state.add_signal(sig)
            await ws_delivery_manager.broadcast_event("signal_detected", sig.model_dump())
            nudge = await nudge_engine.process_signal(sig, q4_state, use_deepseek=False)
            if nudge:
                await ws_delivery_manager.broadcast_nudge(nudge)

        # Step 6: Persist updated transcript
        if settings.save_transcripts:
            session.save_transcript()

        return {
            "call_id": call_id,
            "turn_id": agent_turn.turn_id,
            "customer_text": clean_user_text,
            "agent_text": agent_reply_text,
            "audio_url": audio_url,
            "provider_used": provider_used,
            "qualification": session.loan_application.get_summary_dict(),
            "dialog_action": dialog_meta.get("action"),
            "kb_citation": kb_citation,
            "language": detected_language,
            "voice": selected_voice,
            "latencies": latencies.model_dump(),
        }

    def end_call(self, call_id: str, reason: str = "caller_hangup") -> Dict[str, Any]:
        """
        Completes the call session and returns summary metrics.
        """
        session = self.session_manager.get_session(call_id)
        if not session:
            return {"call_id": call_id, "status": "not_found"}

        session.complete_call(status=reason)
        metrics = session.get_summary_metrics()
        logger.info("[PIPELINE] Call %s ended. Summary: %s", call_id, metrics)

        if call_id in active_call_states:
            active_call_states[call_id].status = "completed"
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(ws_delivery_manager.broadcast_event("call_completed", active_call_states[call_id].get_summary()))
            except Exception:
                pass

        return metrics


voice_pipeline = VoicePipeline()
