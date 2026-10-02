import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from q3.philippines.locale import ph_locale, LanguageDetectionResult
from app.logging_config import logger


class PhilippinesIntentResult(BaseModel):
    """Structured intent representation for Philippines Life Insurance Voice Bot."""
    intent: str = Field(..., description="Detected intent name")
    confidence: float = Field(1.0, description="Confidence score")
    language: str = Field(..., description="'en', 'fil', or 'taglish'")
    code_switch: bool = Field(False, description="Whether utterance is code-switched")
    sector: str = Field("life_insurance", description="Domain sector")
    matched_keywords: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None


class PhilippinesIntentDetector:
    """
    Identifies customer intents in English, Filipino, or Taglish directly
    without machine translation, preserving the local nuance.
    """

    def __init__(self):
        # Patterns for life insurance intents
        self.intent_patterns = {
            "human_escalation": [
                r"\b(?:makausap|kausapin|kumausap)\b.*\b(?:ahente|tao|agent|advisor|manager|representative)\b",
                r"\b(?:speak|talk)\b.*\b(?:human|agent|representative|manager|advisor|specialist|person)\b",
                r"\b(?:transfer|connect)\b.*\b(?:human|agent|call)\b",
                r"\b(?:pwede\s+po\s+ba|pwede\s+ba)\s+(?:ahente|taong\s+tunay|live\s+agent)\b",
                r"\b(?:gusto\s+ko\s+ng\s+tao|tao\s+ang\s+gusto\s+ko)\b"
            ],
            "objection": [
                r"\b(?:mahal|sobrang\s+mahal|masyadong\s+mahal|expensive|pricey|costly|mataas\s+ang\s+premium)\b",
                r"\b(?:wala\s+pa|walang)\b.*\b(?:pera|budget|ipon|cash)\b",
                r"\b(?:no\s+budget|cannot\s+afford|can't\s+afford|tight\s+budget)\b",
                r"\b(?:malugi|malulugi|scam|baka\s+scam|hindi\s+mabayaran|baka\s+mawala)\b",
                r"\b(?:next\s+time|sa\s+susunod|matagal\s+pa\s+naman|bata\s+pa\s+ako)\b"
            ],
            "greeting": [
                r"\b(?:kamusta|kumusta|magandang\s+araw|magandang\s+umaga|magandang\s+hapon|magandang\s+gabi)\b",
                r"\b(?:hello|hi|good\s+morning|good\s+afternoon|good\s+day)\b"
            ],
            "lapse_inquiry": [
                r"\b(?:lapse|mag-lapse|napaso|ma-lapse|lapsed|reinstatement|reinstate)\b",
                r"\b(?:hindi\s+nakabayad|nakalimutang\s+magbayad|missed\s+payment|late\s+payment)\b",
                r"\b(?:grace\s+period|31\s+days|31\s+araw)\b"
            ],
            "premium_information": [
                r"\b(?:magkano\s+yung|magkano\s+ang|magkano\s+po|how\s+much\s+is|what\s+is\s+the)\b.*\b(?:premium|hulog|monthly|bayad|rate|presyo)\b",
                r"\b(?:premium|hulog|payment\s+mode|mode\s+of\s+payment|auto-debit|ada)\b",
                r"\b(?:discount\s+on\s+annual|annual\s+payment|quarterly|semi-annual)\b"
            ],
            "rider_inquiry": [
                r"\b(?:rider|riders|add-on|karagdagang\s+benepisyo)\b",
                r"\b(?:critical\s+illness|cancer|stroke|heart\s+attack|sakit)\b",
                r"\b(?:accidental\s+death|adb|disability|waiver\s+of\s+premium|hospital\s+income)\b"
            ],
            "beneficiary_inquiry": [
                r"\b(?:beneficiary|beneficiaries|benepisyaryo|tatanggap)\b",
                r"\b(?:anak|asawa|magulang|nanay|tatay|spouse|children|dependents)\b",
                r"\b(?:revocable|irrevocable|claim|death\s+claim)\b"
            ],
            "bancassurance_inquiry": [
                r"\b(?:bancassurance|bdo|bpi|metrobank|security\s+bank|bangko|bank\s+referral)\b",
                r"\b(?:bank\s+partner|branch|auto-debit\s+arrangement)\b"
            ],
            "coverage_inquiry": [
                r"\b(?:coverage|face\s+amount|saklaw|halaga\s+ng\s+proteksyon|proteksyon)\b",
                r"\b(?:how\s+much\s+coverage|minimum\s+coverage|maximum\s+coverage|₱500,000|1\s+million|isang\s+milyon)\b"
            ],
            "policy_inquiry": [
                r"\b(?:term\s+life|whole\s+life|vul|unit-linked|secureterm|lifeheritage|investshield)\b",
                r"\b(?:polisa|policy|anong\s+klaseng\s+insurance|types\s+of\s+insurance)\b"
            ],
            "quote_inquiry": [
                r"\b(?:kumuha|apply|mag-apply|quote|quotation|magkano\s+kung|estimate)\b",
                r"\b(?:gusto\s+ko\s+kumuha|i\s+want\s+a\s+quote|interested\s+ako)\b"
            ]
        }

        # Out-of-scope triggers (e.g. food recipes, crypto trading, sports, astronomy)
        self.unsupported_patterns = [
            r"\b(?:bake|cookie|recipe|luto|adobo|sinigang|ulam|restaurant)\b",
            r"\b(?:crypto|bitcoin|ethereum|solana|binance|token|blockchain)\b",
            r"\b(?:weather|panahon|ulan|bagyo|traffic|baha)\b",
            r"\b(?:nba|basketball|football|boxing|movie|sine|k-drama)\b",
            r"\b(?:capital\s+of|president\s+of|history\s+of|astronomy|planet)\b"
        ]

    def detect_intent(self, text: str) -> PhilippinesIntentResult:
        """
        Determines language and intent for an input utterance directly.
        """
        lang_res = ph_locale.detect_language(text)
        clean_text = text.lower().strip()

        # 1. Check for out-of-scope / unsupported questions
        for pattern in self.unsupported_patterns:
            if re.search(pattern, clean_text):
                return PhilippinesIntentResult(
                    intent="unsupported",
                    confidence=0.95,
                    language=lang_res.language,
                    code_switch=lang_res.code_switch,
                    sector="life_insurance",
                    matched_keywords=re.findall(pattern, clean_text),
                    explanation="Out-of-scope non-insurance domain inquiry."
                )

        # 2. Check prioritized intent patterns
        for intent, patterns in self.intent_patterns.items():
            for p in patterns:
                m = re.search(p, clean_text)
                if m:
                    return PhilippinesIntentResult(
                        intent=intent,
                        confidence=0.92,
                        language=lang_res.language,
                        code_switch=lang_res.code_switch,
                        sector="life_insurance",
                        matched_keywords=[m.group(0)],
                        explanation=f"Matched pattern '{p}' for intent '{intent}'."
                    )

        # 3. Check if user is volunteering qualification numbers (e.g., age, amounts, family)
        has_age = bool(re.search(r"\b(?:\d{2}|anyos|years?\s+old)\b", clean_text))
        has_money = bool(re.search(r"\b(?:₱|\bphp\b|pesos?|milyon|libo|thousand|k|million)\b", clean_text))
        has_family = bool(re.search(r"\b(?:asawa|anak|nanay|tatay|wife|husband|kids|children|parents)\b", clean_text))

        if has_age or has_money or has_family:
            return PhilippinesIntentResult(
                intent="qualification_answer",
                confidence=0.85,
                language=lang_res.language,
                code_switch=lang_res.code_switch,
                sector="life_insurance",
                matched_keywords=["qualification_data"],
                explanation="Utterance contains qualification criteria values."
            )

        # 4. Fallback to general policy inquiry if insurance terms are present
        if lang_res.insurance_terms_found:
            return PhilippinesIntentResult(
                intent="policy_inquiry",
                confidence=0.75,
                language=lang_res.language,
                code_switch=lang_res.code_switch,
                sector="life_insurance",
                matched_keywords=lang_res.insurance_terms_found,
                explanation="Contains insurance terms without specific sub-intent."
            )

        # Default fallback
        return PhilippinesIntentResult(
            intent="unsupported",
            confidence=0.60,
            language=lang_res.language,
            code_switch=lang_res.code_switch,
            sector="life_insurance",
            matched_keywords=[],
            explanation="No matching life insurance intent found."
        )


ph_intent_detector = PhilippinesIntentDetector()
