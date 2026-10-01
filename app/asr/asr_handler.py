import time
from typing import Dict, Any, Optional
from app.config import settings
from app.logging_config import logger


class ASRHandler:
    def __init__(self):
        self.provider = settings.asr_provider
        self.language = settings.asr_language

    def process_transcript(
        self,
        text: str,
        client_duration_ms: Optional[float] = None,
        confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Processes incoming speech-to-text transcript from client/telephony.
        Cleans and normalizes the utterance text.
        """
        start = time.perf_counter()
        normalized_text = text.strip()

        # If client provided duration or latency, use it; otherwise estimate
        asr_latency_ms = client_duration_ms if client_duration_ms is not None else (time.perf_counter() - start) * 1000

        logger.info(
            "[ASR] Utterance received: '%s' (Confidence: %s, Latency: %.1fms)",
            normalized_text,
            f"{confidence:.2f}" if confidence is not None else "N/A",
            asr_latency_ms,
        )

        return {
            "text": normalized_text,
            "asr_latency_ms": round(asr_latency_ms, 1),
            "confidence": confidence if confidence is not None else 1.0,
            "provider": self.provider,
        }


asr_handler = ASRHandler()
