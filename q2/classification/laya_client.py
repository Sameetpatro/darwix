import json
import os
import re
import urllib.request
import urllib.error
from typing import Tuple, Dict, Any, Optional
from dotenv import load_dotenv
from app.logging_config import logger

load_dotenv()

LAYA_API_KEY = os.getenv("LAYA_API_KEY")
LAYA_BASE_URL = os.getenv("LAYA_BASE_URL", "https://api.laya.studio/v1").rstrip("/")
LAYA_ENDPOINT = f"{LAYA_BASE_URL}/systemone"


class LayaClassifier:
    """
    Client for Laya System 1 Decision Model (replacing Jev).
    Executes fast, structured non-autoregressive classification:
    - product
    - qualification
    - policy
    - faq
    - objection
    - marketing
    - other
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or LAYA_API_KEY
        self.endpoint = LAYA_ENDPOINT

    def classify_content(self, text: str) -> Tuple[str, float]:
        """
        Classifies business document content into one of the designated categories.
        Returns: (category, confidence)
        """
        clean_text = text.strip()
        if not clean_text:
            return "other", 0.0

        # Sample snippet for classification (first 600 characters is ideal for System 1)
        sample = clean_text[:600]

        # 1. Attempt Laya API
        if self.api_key and not self.api_key.startswith("your_"):
            try:
                payload = {
                    "context": sample,
                    "questions": {
                        "content_type": {
                            "type": "choice",
                            "instructions": "What type of business content is this document section?",
                            "criteria": {
                                "qualification": "Minimum eligibility thresholds, operating age, credit scores, revenue requirements",
                                "product": "Loan structures, loan terms, credit limits, interest rates",
                                "policy": "Company lending policies, geographic restrictions, state rules",
                                "faq": "Frequently asked questions and direct answers",
                                "objection": "Customer hesitation, rate concerns, fee rebuttals",
                                "marketing": "Promotional material, advertisements, customer testimonials",
                                "other": "General or unclassified text",
                            },
                        }
                    },
                }

                req = urllib.request.Request(
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Darwix Q2 Ingestion Engine)",
                    },
                    data=json.dumps(payload).encode("utf-8"),
                )

                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    answer = data.get("answers", {}).get("content_type", {})
                    choice = answer.get("choice", "other")
                    conf = float(answer.get("confidence", 0.8))

                    # If Laya returns a valid category
                    if choice in ["qualification", "product", "policy", "faq", "objection", "marketing", "other"]:
                        logger.info("[LAYA] Classified section as '%s' (Confidence: %.2f)", choice, conf)
                        # If Laya returns 'other' with very low confidence, check rule fallback for exact terms
                        if choice == "other" or conf < 0.2:
                            rule_cat, rule_conf = self._heuristic_fallback(clean_text)
                            if rule_cat != "other":
                                return rule_cat, rule_conf
                        return choice, round(conf, 3)

            except Exception as exc:
                logger.warning("[LAYA] API call failed: %s. Using heuristic classification fallback.", exc)

        # 2. Heuristic fallback (fast, deterministic keyword rules)
        return self._heuristic_fallback(clean_text)

    def _heuristic_fallback(self, text: str) -> Tuple[str, float]:
        """High-precision keyword fallback classifier."""
        lowered = text.lower()

        # FAQ check
        if any(p in lowered for p in ["faq", "question:", "frequently asked questions", "q:", "answer:"]):
            return "faq", 0.95

        # Objection check
        if any(p in lowered for p in ["objection", "hesitant", "concern", "worried", "fees are too high", "rate rebuttal"]):
            return "objection", 0.92

        # Qualification check
        if any(p in lowered for p in [
            "minimum time in business", "operating history", "months in business",
            "minimum monthly revenue", "credit score requirement", "eligibility threshold",
            "qualify", "pre-qualify", "minimum gross"
        ]):
            return "qualification", 0.90

        # Product check
        if any(p in lowered for p in [
            "term loan", "line of credit", "equipment financing", "sba 7",
            "interest rate", "loan amount", "revolving", "apr", "working capital loan"
        ]):
            return "product", 0.88

        # Policy check
        if any(p in lowered for p in [
            "policy", "restricted industries", "ineligible", "geographic coverage",
            "50 states", "prohibited", "leverage ratio", "compliance"
        ]):
            return "policy", 0.85

        # Marketing check
        if any(p in lowered for p in ["apply today", "testimonials", "trusted by thousands", "grow your business"]):
            return "marketing", 0.75

        return "other", 0.50


laya_classifier = LayaClassifier()
