import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# Mandatory Indonesian Consumer Finance Terminology
REQUIRED_FINANCE_TERMINOLOGY = {
    "cicilan": {
        "term": "cicilan",
        "description": "Installments / periodic scheduled repayments."
    },
    "tenor": {
        "term": "tenor",
        "description": "Duration or repayment period of the financing contract (e.g. 12, 24, 36 months)."
    },
    "denda": {
        "term": "denda",
        "description": "Late payment penalty fee (0.5% per calendar day after grace period)."
    },
    "dp": {
        "term": "dp",
        "description": "Down Payment / uang muka (standard 10% to 20% per OJK regulations)."
    },
    "jatuh tempo": {
        "term": "jatuh tempo",
        "description": "Due date / repayment cut-off date each month."
    },
    "angsuran": {
        "term": "angsuran",
        "description": "Monthly installment payment amount."
    },
    "pembiayaan": {
        "term": "pembiayaan",
        "description": "Multifinance / consumer loan facility."
    }
}

# English finance terms commonly code-switched in Indonesian consumer speech
ENGLISH_FINANCE_TERMS = {
    "late fee", "grace period", "down payment", "reschedule", "restructuring",
    "installment", "due date", "penalty", "overdue", "waiver", "waive", "payment",
    "virtual account", "va", "transfer", "customer service", "cs"
}

# Colloquial Indonesian markers (Bahasa Gaul / Informal)
COLLOQUIAL_MARKERS = {
    "nggak", "gak", "ga", "ngga", "udah", "udh", "ntar", "gitu", "aja", "doang",
    "banget", "bgt", "dong", "sih", "nih", "deh", "kok", "lho", "loh", "yuk",
    "gimana", "gmn", "kenapa", "knp", "emang", "kan", "kak", "min", "bro", "bisa",
    "pengen", "mau", "kalo", "kalau", "telat", "bayar", "motor", "mobil", "duit", "uang"
}

# Regional dialect markers across Indonesia
REGIONAL_MARKERS = {
    # Javanese influences (Jawa Tengah / Jawa Timur / Yogyakarta)
    "javanese": {
        "monggo", "piye", "rek", "sampun", "boten", "mboten", "wae", "nggih",
        "ndak", "lho", "toh", "yo", "piye kabare", "wes", "mari"
    },
    # Sundanese influences (Jawa Barat)
    "sundanese": {
        "teh", "mah", "atuh", "euy", "kumaha", "pisan", "mangga", "da"
    },
    # Medan / North Sumatra influences
    "medan": {
        "bah", "lah", "wak", "kelen", "cemana", "kali", "tengok"
    }
}

# Formal Indonesian vocabulary indicators
FORMAL_MARKERS = {
    "selamat", "siang", "pagi", "sore", "malam", "apakah", "bagaimanakah",
    "perihal", "ketentuan", "keterlambatan", "pembayaran", "mohon", "terima", "kasih",
    "berkenan", "menanyakan", "mengajukan", "fasilitas", "konsumen", "nasabah"
}


class IndonesianLanguageResult(BaseModel):
    """Structured representation of Indonesian language, dialect, and code-switching."""
    language: str = Field("id", description="'id' or 'en'")
    dialect_style: str = Field("colloquial", description="'formal', 'colloquial', 'regional', or 'code_switched'")
    code_switch: bool = Field(False, description="True if Indonesian and English terms are mixed")
    detected_markers: List[str] = Field(default_factory=list)
    regional_dialect: Optional[str] = Field(None, description="e.g. 'javanese', 'sundanese', 'medan'")
    finance_terms_found: List[str] = Field(default_factory=list)
    confidence: float = Field(1.0, description="Detection confidence 0.0 to 1.0")


class IndonesiaLocaleEngine:
    """
    Directly analyzes Indonesian customer utterances (formal, colloquial, regional,
    and code-switched with English finance terms) without prior translation.
    """

    def detect_language(self, text: str) -> IndonesianLanguageResult:
        clean = text.lower().strip()
        tokens = re.findall(r"\b[a-zA-Z0-9-]+\b", clean)

        if not tokens:
            return IndonesianLanguageResult(language="id", dialect_style="colloquial")

        # 1. Search for mandatory finance terminology
        finance_found = []
        for term in REQUIRED_FINANCE_TERMINOLOGY.keys():
            if term == "dp":
                if re.search(r"\b(?:dp|down\s*payment|uang\s*muka)\b", clean):
                    finance_found.append("DP")
            elif term == "jatuh tempo":
                if "jatuh tempo" in clean or "due date" in clean:
                    finance_found.append("jatuh tempo")
            else:
                if re.search(rf"\b{re.escape(term)}\b", clean):
                    finance_found.append(term)

        # 2. Check for English finance terms (Code-Switching)
        en_terms_found = []
        for en_t in ENGLISH_FINANCE_TERMS:
            if re.search(rf"\b{re.escape(en_t)}\b", clean):
                en_terms_found.append(en_t)

        is_code_switch = len(en_terms_found) > 0 and any(t in clean for t in ["kalau", "kalo", "saya", "ada", "nggak", "gak", "bisa", "mau", "cicilan", "angsuran", "denda"])

        # 3. Check for regional markers
        detected_region = None
        regional_markers_found = []
        for region, markers in REGIONAL_MARKERS.items():
            for m in markers:
                if re.search(rf"\b{re.escape(m)}\b", clean):
                    detected_region = region
                    regional_markers_found.append(m)

        # 4. Check formal vs colloquial markers
        colloquial_found = [tok for tok in tokens if tok in COLLOQUIAL_MARKERS]
        formal_found = [tok for tok in tokens if tok in FORMAL_MARKERS]

        # Determine dialect style
        if is_code_switch:
            dialect_style = "code_switched"
        elif detected_region:
            dialect_style = "regional"
        elif len(formal_found) > len(colloquial_found) and not any(t in tokens for t in ["nggak", "gak", "dong", "sih", "nih"]):
            dialect_style = "formal"
        else:
            dialect_style = "colloquial"

        # Check pure English utterance
        pure_en_tokens = {"what", "how", "when", "why", "can", "i", "is", "there", "my", "the", "please"}
        if len([t for t in tokens if t in pure_en_tokens]) >= 2 and not colloquial_found and not formal_found:
            lang = "en"
        else:
            lang = "id"

        detected_markers_all = list(set(colloquial_found + formal_found + regional_markers_found + en_terms_found))

        return IndonesianLanguageResult(
            language=lang,
            dialect_style=dialect_style,
            code_switch=is_code_switch,
            detected_markers=detected_markers_all,
            regional_dialect=detected_region,
            finance_terms_found=list(set(finance_found)),
            confidence=0.95
        )

    def extract_finance_terms(self, text: str) -> Dict[str, Any]:
        """Extracts recognized Indonesian consumer finance terminology."""
        clean = text.lower()
        matched = {}
        for term, meta in REQUIRED_FINANCE_TERMINOLOGY.items():
            if term == "dp":
                if re.search(r"\b(?:dp|down\s*payment|uang\s*muka)\b", clean):
                    matched[term] = meta
            elif term == "jatuh tempo":
                if "jatuh tempo" in clean or "due date" in clean:
                    matched[term] = meta
            else:
                if re.search(rf"\b{re.escape(term)}\b", clean):
                    matched[term] = meta
        return matched


id_locale = IndonesiaLocaleEngine()
