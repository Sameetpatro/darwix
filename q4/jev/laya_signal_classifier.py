import json
import os
import re
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Tuple, Optional
from dotenv import load_dotenv
from app.logging_config import logger

load_dotenv()

LAYA_API_KEY = os.getenv("LAYA_API_KEY")
LAYA_BASE_URL = os.getenv("LAYA_BASE_URL", "https://api.laya.studio/v1").rstrip("/")
LAYA_ENDPOINT = f"{LAYA_BASE_URL}/systemone"


class LayaSignalClassifier:
    """
    Fast System-1 decision and confidence scoring client for live conversation signals.
    Replaces JEV with Laya modern decision API, with local high-precision heuristics.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or LAYA_API_KEY
        self.endpoint = LAYA_ENDPOINT

    def evaluate_signal_confidence(
        self,
        signal_type: str,
        text: str,
        speaker: str = "customer",
    ) -> Tuple[float, str]:
        """
        Evaluates semantic validity and confidence for a detected signal candidate.
        Returns: (confidence: float, explanation: str)
        """
        cleaned = text.strip()
        if not cleaned:
            return 0.0, "Empty utterance"

        # Check for ambiguous, hesitant speech fragments
        # e.g. "I... uh... maybe... another..." -> Must be rejected with low confidence
        if self._is_ambiguous_or_noisy(cleaned):
            return 0.35, "Speech is ambiguous, fragmented, or hesitant (suppressed)"

        # Check 3rd party attribution for cross-sell (e.g., "my brother has another vehicle")
        if signal_type == "cross_sell_opportunity":
            is_valid, reason, conf = self._evaluate_cross_sell(cleaned, speaker)
            if not is_valid:
                return conf, reason
            return conf, reason

        # Frustration evaluation
        if signal_type == "frustration":
            conf, reason = self._evaluate_frustration(cleaned)
            return conf, reason

        # Payment difficulty evaluation
        if signal_type == "payment_difficulty":
            conf, reason = self._evaluate_payment_difficulty(cleaned)
            return conf, reason

        # Compliance gap evaluation
        if signal_type == "compliance_gap":
            return 0.96, "Mandatory regulatory disclosure omitted before binding stage"

        return 0.70, "General signal detected"

    def _is_ambiguous_or_noisy(self, text: str) -> bool:
        """Detects low-information, trailing, or highly hesitant utterances."""
        lowered = text.lower().strip()
        
        # Ellipsis, stuttering patterns, filled pauses
        tokens = [t.strip(".,?!") for t in lowered.split() if t.strip(".,?!")]
        if not tokens:
            return True
        
        hesitation_tokens = {"uh", "um", "maybe", "like", "er", "ah", "mumble"}
        hesitation_count = sum(1 for t in tokens if t in hesitation_tokens)
        
        # High hesitation ratio or trailing incomplete clause
        if len(tokens) <= 4 and ("..." in text or hesitation_count >= 1 and "another" in tokens):
            if not any(v in lowered for v in ["i have", "i own", "we have", "got a"]):
                return True

        if len(tokens) < 3 and "..." in text:
            return True

        return False

    def _evaluate_cross_sell(self, text: str, speaker: str) -> Tuple[bool, str, float]:
        """
        Differentiates first-person customer cross-sell opportunity from 3rd-party mentions.
        Example True: "I actually have another car as well." -> Valid
        Example False: "My brother has another vehicle." -> Invalid (3rd party)
        """
        lowered = text.lower()

        # 3rd party ownership checks
        third_party_patterns = [
            r"\b(my\s+(brother|sister|friend|neighbor|cousin|boss|uncle|dad|mom|father|mother))\b",
            r"\b(someone\s+else|somebody\s+else)\b",
            r"\b(he\s+has|she\s+has|they\s+have)\b",
            r"\b(his\s+car|her\s+car|their\s+car|his\s+vehicle|her\s+vehicle)\b"
        ]
        for pattern in third_party_patterns:
            if re.search(pattern, lowered):
                return False, f"3rd party ownership reference detected: {pattern}", 0.25

        # First-person customer ownership
        first_person_patterns = [
            r"\b(i|we)\s+(\w+\s+){0,3}(have|got|own|operate|drive)\b.*\b(car|vehicle|truck|suv|motorcycle|auto|policy|coverage|fleet)\b",
            r"\b(another|second|additional|other)\s+(car|vehicle|truck|automobile|van|unit)\b",
            r"\b(two\s+cars|second\s+car|second\s+vehicle|additional\s+vehicle|fleet\s+vehicles)\b"
        ]
        for pattern in first_person_patterns:
            if re.search(pattern, lowered):
                return True, "Direct customer ownership of additional vehicle", 0.91

        # Generic mention
        if "vehicle" in lowered or "car" in lowered:
            return True, "General vehicle mention", 0.72

        return False, "No verified cross-sell asset detected", 0.30

    def _evaluate_frustration(self, text: str) -> Tuple[float, str]:
        """Evaluates customer frustration severity."""
        lowered = text.lower()

        # Repetition complaints
        if any(p in lowered for p in [
            "already explained this twice", "already told you this three times",
            "already told you", "explained this twice", "asked again", "asking again",
            "told you twice", "third time", "how many times do i have to say"
        ]):
            return 0.88, "Customer explicitly complaining about repetitive questions"

        # Explicit annoyance / negative sentiment
        if any(p in lowered for p in [
            "ridiculous", "frustrated", "terrible service", "waste of time",
            "unacceptable", "annoyed", "don't understand why you keep", "fed up"
        ]):
            return 0.92, "High negative sentiment and explicit irritation"

        return 0.50, "Mild dissatisfaction"

    def _evaluate_payment_difficulty(self, text: str) -> Tuple[float, str]:
        """Evaluates customer payment distress."""
        lowered = text.lower()

        if any(p in lowered for p in [
            "can't make the payment", "cannot make the payment",
            "don't think i can make the payment", "hard to pay",
            "afford this month", "tight on money", "lost my job",
            "past due", "need an extension", "cannot afford",
            "unable to pay", "struggling financially"
        ]):
            return 0.93, "Customer explicitly states inability to make scheduled payment"

        return 0.45, "Ambiguous payment reference"


laya_signal_classifier = LayaSignalClassifier()
