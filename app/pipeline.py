import time
from typing import Dict, Any, Optional
from app.config import settings
from app.logging_config import logger
from app.state import session_manager, CallSession, LatencyBreakdown
from app.llm.deepseek import deepseek_client, clean_text_for_speech
from app.tts.edge_tts_engine import tts_engine
from app.asr.asr_handler import asr_handler
from app.qualification.dialog_manager import dialog_manager

INITIAL_AGENT_GREETING = "Hello! Thank you for calling Darwix. I'm Vani, your business loan specialist. How can I assist you with your financing needs today?"


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

        # Step 3: Run Qualification Dialog Engine (slot extraction, conflict detection, rules, objections, escalation)
        llm_start = time.perf_counter()
        target_reply, dialog_meta = self.dialog_manager.process_turn(
            app=session.loan_application,
            user_utterance=clean_user_text,
            turn_number=len(session.turns),
        )

        # Handle escalation status update
        if dialog_meta.get("action") == "escalate":
            session.status = "escalated"
        elif dialog_meta.get("action") == "underwriting_decision":
            dec_status = dialog_meta.get("decision", {}).get("status")
            if dec_status:
                session.status = f"underwriting_{dec_status.lower()}"

        # If DeepSeek is configured and healthy, we can enrich dialog prompt
        provider_used = "qualification_dialog_engine"
        agent_reply_text = clean_text_for_speech(target_reply)
        llm_ms = (time.perf_counter() - llm_start) * 1000

        # Step 4: Synthesize TTS Audio
        turn_num = len(session.turns) + 1
        audio_url, audio_path, tts_ms = await self.tts.synthesize(
            text=agent_reply_text,
            call_id=call_id,
            turn_id=turn_num,
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
            kb_citation=dialog_meta.get("kb_citation"),
        )

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
            "kb_citation": dialog_meta.get("kb_citation"),
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
        return metrics


voice_pipeline = VoicePipeline()
