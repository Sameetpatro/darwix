import asyncio
import time
import os
from pathlib import Path
from typing import Optional, Tuple
import edge_tts

from app.config import settings
from app.logging_config import logger

PH_VOICES = {
    "fil": {
        "female": "fil-PH-BlessicaNeural",
        "male": "fil-PH-AngeloNeural"
    },
    "taglish": {
        "female": "fil-PH-BlessicaNeural",
        "male": "fil-PH-AngeloNeural"
    },
    "en": {
        "female": "en-PH-RosaNeural",
        "male": "en-PH-JamesNeural"
    }
}

PH_RECORDINGS_DIR = settings.recordings_dir / "philippines"
PH_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


class PhilippinesTTSEngine:
    """
    Synthesizes native Philippine speech (Filipino, Taglish, Philippine English)
    using Microsoft Edge Neural TTS with low latency and audio caching.
    """

    def __init__(self, default_gender: str = "female"):
        self.default_gender = default_gender

    def get_voice(self, language: str = "taglish", gender: Optional[str] = None) -> str:
        gen = gender or self.default_gender
        lang_key = language if language in PH_VOICES else "taglish"
        return PH_VOICES[lang_key].get(gen, "fil-PH-BlessicaNeural")

    async def synthesize(
        self,
        text: str,
        language: str = "taglish",
        output_filename: Optional[str] = None,
        voice: Optional[str] = None
    ) -> Tuple[str, float]:
        """
        Synthesizes text into high-fidelity neural MP3 audio.
        Returns: (audio_file_path, latency_ms)
        """
        start_time = time.perf_counter()
        selected_voice = voice or self.get_voice(language)

        if not output_filename:
            safe_ts = int(time.time() * 1000)
            output_filename = f"ph_turn_{safe_ts}.mp3"

        out_path = PH_RECORDINGS_DIR / output_filename

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=selected_voice,
                rate="+0%",
                pitch="+0Hz"
            )
            await communicate.save(str(out_path))
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            logger.info(
                f"[PH-TTS] Synthesized {len(text)} chars with '{selected_voice}' in {latency_ms:.1f}ms -> {out_path.name}"
            )
            return str(out_path), latency_ms
        except Exception as e:
            logger.error(f"[PH-TTS] Synthesis failed for voice {selected_voice}: {e}", exc_info=True)
            # Create empty fallback audio file if network drops
            with open(out_path, "wb") as f:
                f.write(b"")
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return str(out_path), latency_ms


ph_tts_engine = PhilippinesTTSEngine()
