import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from q3.indonesia.locale import id_locale, IndonesianLanguageResult


class IndonesianIntentResult(BaseModel):
    """Structured intent representation for Indonesian Consumer Finance Voice Bot."""
    intent: str = Field(..., description="Detected intent name")
    confidence: float = Field(1.0, description="Confidence score")
    language: str = Field("id", description="'id' or 'en'")
    code_switch: bool = Field(False, description="True if English code-switching is present")
    sector: str = Field("consumer_finance", description="Domain sector")
    dialect_style: str = Field("colloquial", description="formal, colloquial, regional, code_switched")
    matched_keywords: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None


class IndonesianIntentDetector:
    """
    Identifies customer intents in Indonesian consumer finance directly
    without machine translation.
    """

    def __init__(self):
        self.intent_patterns = {
            "human_escalation": [
                r"\b(?:bicara|ngomong|sambungkan|hubungkan)\b.*\b(?:cs|customer\s*service|manusia|orang|agen|staf|representative|petugas)\b",
                r"\b(?:speak|talk)\b.*\b(?:human|agent|representative|specialist)\b",
                r"\b(?:mau\s+(?:ngomong|bicara)\s+sama\s+(?:orang|cs|manusia))\b",
                r"\b(?:tolong\s+sambungkan\s+ke\s+(?:agen|cs|staf))\b"
            ],
            "payment_objection": [
                r"\b(?:denda.*(?:terlalu\s*tinggi|kemahalan|mahal|berat|tinggi\s*banget|kebanyakan))\b",
                r"\b(?:belum\s*ada\s*(?:dana|uang|duit)|lagi\s*seret|gajian\s*belum\s*cair|nggak\s*ada\s*duit)\b",
                r"\b(?:bisa\s*minta\s*(?:keringanan\s*denda|potongan\s*denda|hapus\s*denda))\b"
            ],
            "late_payment_fee": [
                r"\b(?:late\s*fee|denda|denda\s*keterlambatan|biaya\s*telat|penalty)\b",
                r"\b(?:kalau\s*telat|kalo\s*telat|terlambat\s*bayar|lewat\s*jatuh\s*tempo)\b",
                r"\b(?:grace\s*period|masa\s*tenggang)\b"
            ],
            "payment_methods": [
                r"\b(?:cara\s*bayar|bayar\s*(?:lewat|pake|via|di)|metode\s*pembayaran)\b",
                r"\b(?:virtual\s*account|va|indomaret|alfamart|gopay|ovo|dana|shopeepay|atm|m-banking)\b"
            ],
            "due_date_inquiry": [
                r"\b(?:jatuh\s*tempo|due\s*date|kapan\s*(?:harus\s*bayar|batas\s*bayar|terakhir))\b",
                r"\b(?:tanggal\s*berapa\s*jatuh\s*tempo)\b"
            ],
            "restructuring_inquiry": [
                r"\b(?:restrukturisasi|keringanan\s*cicilan|perpanjang\s*tenor|reschedule|ganti\s*tenor)\b",
                r"\b(?:cicilan\s*terlalu\s*berat|pengen\s*kecilin\s*angsuran)\b"
            ],
            "early_payoff": [
                r"\b(?:pelunasan\s*dipercepat|lunasin\s*sekarang|tutup\s*kontrak|bayar\s*lunas)\b"
            ]
        }

        # Out-of-scope triggers
        self.unsupported_patterns = [
            r"\b(?:resep|masak|baking|cookies|kue|rendang|nasi\s*goreng|restoran)\b",
            r"\b(?:crypto|bitcoin|ethereum|solana|binance|blockchain)\b",
            r"\b(?:cuaca|hujan|banjir|macet|gempa|prakiraan)\b",
            r"\b(?:sepak\s*bola|liga|presiden|ibukota|astronomi|film)\b"
        ]

    def detect_intent(self, text: str) -> IndonesianIntentResult:
        lang_res = id_locale.detect_language(text)
        clean = text.lower().strip()

        # 1. Out-of-scope inquiry check
        for pattern in self.unsupported_patterns:
            if re.search(pattern, clean):
                return IndonesianIntentResult(
                    intent="unsupported",
                    confidence=0.95,
                    language=lang_res.language,
                    code_switch=lang_res.code_switch,
                    sector="consumer_finance",
                    dialect_style=lang_res.dialect_style,
                    matched_keywords=re.findall(pattern, clean),
                    explanation="Out-of-scope non-finance inquiry."
                )

        # 2. Check prioritized intent patterns
        for intent, patterns in self.intent_patterns.items():
            for p in patterns:
                m = re.search(p, clean)
                if m:
                    return IndonesianIntentResult(
                        intent=intent,
                        confidence=0.92,
                        language=lang_res.language,
                        code_switch=lang_res.code_switch,
                        sector="consumer_finance",
                        dialect_style=lang_res.dialect_style,
                        matched_keywords=[m.group(0)],
                        explanation=f"Matched pattern '{p}' for intent '{intent}'."
                    )

        # 3. Check general finance keywords
        if lang_res.finance_terms_found:
            return IndonesianIntentResult(
                intent="general_installment_inquiry",
                confidence=0.75,
                language=lang_res.language,
                code_switch=lang_res.code_switch,
                sector="consumer_finance",
                dialect_style=lang_res.dialect_style,
                matched_keywords=lang_res.finance_terms_found,
                explanation="Contains installment/multifinance terms without specific sub-intent."
            )

        # Default fallback
        return IndonesianIntentResult(
            intent="unsupported",
            confidence=0.60,
            language=lang_res.language,
            code_switch=lang_res.code_switch,
            sector="consumer_finance",
            dialect_style=lang_res.dialect_style,
            matched_keywords=[],
            explanation="No matching consumer finance intent found."
        )


id_intent_detector = IndonesianIntentDetector()
