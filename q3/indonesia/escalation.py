import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class IndonesianEscalationHandler:
    """
    Detects customer requests to speak with a human customer service officer
    or debt counseling agent at Darwix Multifinance.
    """

    def is_escalation(self, text: str) -> bool:
        clean = text.lower().strip()
        patterns = [
            r"\b(?:bicara|ngomong|sambungkan|hubungkan)\b.*\b(?:cs|customer\s*service|manusia|orang|agen|staf|representative|petugas)\b",
            r"\b(?:speak|talk)\b.*\b(?:human|agent|representative|specialist)\b",
            r"\b(?:mau\s+(?:ngomong|bicara)\s+sama\s+(?:orang|cs|manusia))\b",
            r"\b(?:tolong\s+sambungkan\s+ke\s+(?:agen|cs|staf))\b"
        ]
        return any(bool(re.search(p, clean)) for p in patterns)

    def get_escalation_response(self, dialect_style: str = "colloquial") -> str:
        if dialect_style == "formal":
            return (
                "Baik Bapak/Ibu, saya segera sambungkan Anda dengan Petugas Layanan Konsumen Darwix Multifinance. "
                "Mohon ditunggu sebentar ya, panggilan Anda sedang kami alihkan agar dapat dibantu secara langsung."
            )
        else:
            return (
                "Siap kak! Saya langsung sambungkan panggilan kakak ke Customer Service Darwix Multifinance ya. "
                "Ditunggu sebentar ya kak, panggilan sedang dialihkan."
            )


id_escalation_handler = IndonesianEscalationHandler()
