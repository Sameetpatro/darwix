import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class PhilippinesEscalationHandler:
    """
    Detects customer requests for human assistance or complex underwriting
    escalation, facilitating a warm transfer to a licensed Financial Advisor.
    """

    def is_escalation(self, text: str) -> bool:
        clean = text.lower().strip()
        patterns = [
            r"\b(?:makausap|kausapin|kumausap)\b.*\b(?:ahente|tao|agent|advisor|manager|representative)\b",
            r"\b(?:speak|talk)\b.*\b(?:human|agent|representative|manager|advisor|specialist|person)\b",
            r"\b(?:transfer|connect)\b.*\b(?:human|agent|advisor|specialist|call)\b",
            r"\b(?:pwede\s+po\s+ba|pwede\s+ba)\s+(?:ahente|taong\s+tunay|live\s+agent)\b",
            r"\b(?:gusto\s+ko\s+ng\s+tao|tao\s+ang\s+gusto\s+ko)\b"
        ]
        return any(bool(re.search(p, clean)) for p in patterns)

    def get_escalation_response(self, language: str = "taglish") -> str:
        """Returns warm transfer response preserving caller language."""
        if language == "fil":
            return (
                "Maliwanag po. Ikokonekta ko po kayo ngayon din sa isa sa aming lisensyadong Financial Advisors sa Darwix Life Bancassurance. "
                "Sandali lamang po habang inililipat ko ang inyong tawag upang matulungan kayo nang personal."
            )
        elif language == "en":
            return (
                "Certainly. I will connect you right away with one of our licensed Financial Advisors at Darwix Life Bancassurance. "
                "Please hold on for just a moment while I transfer your call to assist you personally."
            )
        else: # taglish
            return (
                "Sige po! Ikokonekta ko po kayo agad sa isa sa aming licensed Financial Advisors sa Darwix Life Bancassurance. "
                "Sandali lamang po habang inililipat ko ang inyong tawag para matulungan kayo personally."
            )


ph_escalation_handler = PhilippinesEscalationHandler()
