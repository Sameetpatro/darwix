import time
import uuid
from pathlib import Path
from typing import Tuple, Optional
import edge_tts
from app.config import settings
from app.logging_config import logger


class TTSEngine:
    def __init__(self):
        self.voice = settings.tts_voice
        self.rate = settings.tts_rate
        self.pitch = settings.tts_pitch

    async def synthesize(
        self,
        text: str,
        call_id: Optional[str] = None,
        turn_id: Optional[int] = None,
        voice: Optional[str] = None,
    ) -> Tuple[str, str, float]:
        """
        Synthesizes text into MP3 audio using Edge-TTS neural voice.
        Returns: (relative_audio_url, absolute_file_path, latency_ms)
        """
        start_time = time.perf_counter()
        settings.ensure_directories()

        # Sanitize text
        clean_text = text.strip()
        if not clean_text:
            clean_text = "..."

        file_stem = f"{call_id or 'call'}_turn_{turn_id or uuid.uuid4().hex[:6]}"
        file_name = f"{file_stem}.mp3"
        dest_path = settings.recordings_dir / file_name
        selected_voice = voice or self.voice

        try:
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=selected_voice,
                rate=self.rate,
                pitch=self.pitch,
            )
            await communicate.save(str(dest_path))

            latency_ms = (time.perf_counter() - start_time) * 1000
            relative_url = f"/recordings/{file_name}"

            logger.info(
                "[TTS] Synthesized %d characters in %.1fms -> %s",
                len(clean_text),
                latency_ms,
                file_name,
            )
            return relative_url, str(dest_path), latency_ms

        except Exception as exc:
            logger.error("[TTS] Edge-TTS synthesis failed: %s", exc)
            latency_ms = (time.perf_counter() - start_time) * 1000
            # Return empty or fallback
            return "", "", latency_ms


tts_engine = TTSEngine()
