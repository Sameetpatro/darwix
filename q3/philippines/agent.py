import asyncio
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from q3.philippines.dialog_manager import ph_dialog_manager, PhilippinesConversationSession
from q3.philippines.tts import ph_tts_engine
from app.logging_config import logger


class PhilippinesVoiceAgent:
    """
    Complete Autonomous Voice Agent for Philippines Life Insurance and Bancassurance.
    Understands English, Filipino, and Taglish natively without translation.
    """

    def __init__(self):
        self.dialog_manager = ph_dialog_manager
        self.tts = ph_tts_engine

    def start_call(self, session_id: str, language: str = "taglish") -> Dict[str, Any]:
        """Starts a call session and produces greeting."""
        t0 = time.perf_counter()
        greeting_text = self.dialog_manager.greet(session_id, language)
        return {
            "session_id": session_id,
            "text": greeting_text,
            "language": language,
            "intent": "greeting",
            "latency_ms": (time.perf_counter() - t0) * 1000.0
        }

    async def handle_turn(
        self,
        session_id: str,
        user_utterance: str,
        synthesize_audio: bool = True
    ) -> Dict[str, Any]:
        """
        Coordinates full turn:
        1. Dialog management & Q2 hybrid retrieval
        2. Localized response generation
        3. Edge-TTS neural speech synthesis
        """
        turn_start = time.perf_counter()
        
        # Dialog & RAG
        dialog_res = self.dialog_manager.process_utterance(session_id, user_utterance)
        resp_text = dialog_res["response"]
        lang = dialog_res["language"]

        # TTS Synthesis
        audio_path = None
        tts_lat = 0.0
        if synthesize_audio and resp_text:
            safe_ts = int(time.time() * 1000)
            fname = f"{session_id}_turn_{safe_ts}.mp3"
            audio_path, tts_lat = await self.tts.synthesize(
                text=resp_text,
                language=lang,
                output_filename=fname
            )

        total_lat = (time.perf_counter() - turn_start) * 1000.0

        session = self.dialog_manager.get_or_create_session(session_id)

        return {
            "session_id": session_id,
            "user_utterance": user_utterance,
            "agent_response": resp_text,
            "language": lang,
            "intent": dialog_res["intent"],
            "escalated": dialog_res["escalated"],
            "completed": dialog_res["completed"],
            "citation": dialog_res["citation"],
            "evidence": dialog_res["evidence"],
            "missing_slots": dialog_res["missing_slots"],
            "qualification_profile": session.profile.model_dump(),
            "audio_path": audio_path,
            "tts_latency_ms": tts_lat,
            "total_latency_ms": total_lat
        }


ph_voice_agent = PhilippinesVoiceAgent()
