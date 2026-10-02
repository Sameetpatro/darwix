import asyncio
import time
from pathlib import Path
from typing import Optional, Tuple
import edge_tts

from app.config import settings
from app.logging_config import logger

ID_VOICES = {
    "female": "id-ID-GadisNeural",
    "male": "id-ID-ArdiNeural"
}

ID_RECORDINGS_DIR = settings.recordings_dir / "indonesia"
ID_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


class IndonesianTTSEngine:
    """
    Synthesizes native Indonesian speech using Microsoft Edge Neural TTS:
    - id-ID-GadisNeural (Female)
    - id-ID-ArdiNeural (Male)
    """

    def __init__(self, default_gender: str = "female"):
        self.default_gender = default_gender

    def get_voice(self, gender: Optional[str] = None) -> str:
        gen = gender or self.default_gender
        return ID_VOICES.get(gen, "id-ID-GadisNeural")

    async def synthesize(
        self,
        text: str,
        output_filename: Optional[str] = None,
        voice: Optional[str] = None
    ) -> Tuple[str, float]:
        start_time = time.perf_counter()
        selected_voice = voice or self.get_voice()

        if not output_filename:
            safe_ts = int(time.time() * 1000)
            output_filename = f"id_turn_{safe_ts}.mp3"

        out_path = ID_RECORDINGS_DIR / output_filename

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
                f"[ID-TTS] Synthesized {len(text)} chars with '{selected_voice}' in {latency_ms:.1f}ms -> {out_path.name}"
            )
            return str(out_path), latency_ms
        except Exception as e:
            logger.error(f"[ID-TTS] Synthesis failed for voice {selected_voice}: {e}", exc_info=True)
            with open(out_path, "wb") as f:
                f.write(b"")
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return str(out_path), latency_ms


id_tts_engine = IndonesianTTSEngine()
