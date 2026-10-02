import asyncio
import time
from typing import Dict, Any, Optional
from pathlib import Path

from q3.indonesia.dialog_manager import id_dialog_manager, IndonesianConversationSession
from q3.indonesia.tts import id_tts_engine
from app.logging_config import logger


class IndonesianVoiceAgent:
    """
    Autonomous Voice Agent for Indonesian Consumer Finance & Multifinance.
    Handles Formal, Colloquial, Regional, and Code-Switched speech.
    """

    def __init__(self):
        self.dialog_manager = id_dialog_manager
        self.tts = id_tts_engine

    def start_call(self, session_id: str, dialect_style: str = "colloquial") -> Dict[str, Any]:
        t0 = time.perf_counter()
        greeting_text = self.dialog_manager.greet(session_id, dialect_style)
        return {
            "session_id": session_id,
            "text": greeting_text,
            "language": "id",
            "dialect_style": dialect_style,
            "intent": "greeting",
            "latency_ms": (time.perf_counter() - t0) * 1000.0
        }

    async def handle_turn(
        self,
        session_id: str,
        user_utterance: str,
        synthesize_audio: bool = True
    ) -> Dict[str, Any]:
        turn_start = time.perf_counter()

        # Dialog management & Q2 hybrid search
        dialog_res = self.dialog_manager.process_utterance(session_id, user_utterance)
        resp_text = dialog_res["response"]

        # TTS Synthesis with id-ID-GadisNeural
        audio_path = None
        tts_lat = 0.0
        if synthesize_audio and resp_text:
            safe_ts = int(time.time() * 1000)
            fname = f"{session_id}_turn_{safe_ts}.mp3"
            audio_path, tts_lat = await self.tts.synthesize(
                text=resp_text,
                output_filename=fname
            )

        total_lat = (time.perf_counter() - turn_start) * 1000.0
        session = self.dialog_manager.get_or_create_session(session_id)

        return {
            "session_id": session_id,
            "user_utterance": user_utterance,
            "agent_response": resp_text,
            "language": dialog_res["language"],
            "dialect_style": dialog_res["dialect_style"],
            "intent": dialog_res["intent"],
            "escalated": dialog_res["escalated"],
            "evidence": dialog_res["evidence"],
            "citation": dialog_res["citation"],
            "support_path_offered": dialog_res["support_path_offered"],
            "account_context": session.account_context.model_dump(),
            "audio_path": audio_path,
            "tts_latency_ms": tts_lat,
            "total_latency_ms": total_lat
        }


id_voice_agent = IndonesianVoiceAgent()
