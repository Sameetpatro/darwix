import re
from typing import Dict, Any, List, Tuple
from pydantic import BaseModel, Field

# Core Filipino / Tagalog grammatical markers, honorifics, and common words
FILIPINO_MARKERS = {
    # Honorifics & Politeness
    "po", "opo", "ho", "oho",
    
    # Pronouns & Deictics
    "ako", "ko", "akin", "ikaw", "ka", "mo", "iyo", "siya", "niya", "kaniya",
    "kami", "namin", "amin", "tayo", "natin", "atin", "kayo", "ninyo", "inyo",
    "sila", "nila", "kanila", "ito", "nito", "dito", "diyan", "doon", "iyan", "iyon",
    "yung", "kong", "mong", "inyong", "aming", "ating", "kanilang", "aking", "kanyang",
    
    # Prepositions, Markers & Inversion
    "ang", "si", "sina", "ng", "ni", "nina", "mga", "sa", "kay", "kina", "ay", "pong",
    
    # Common Conjunctions & Particles
    "at", "o", "pero", "kasi", "dahil", "kung", "kapag", "para", "upang",
    "ba", "na", "pa", "naman", "nga", "pala", "daw", "raw", "sana", "yata",
    "hindi", "di", "oo", "sige", "ayos", "kahit", "habang", "tulad", "gayon",
    
    # Common Verbs & Question Words
    "gusto", "nais", "ayaw", "pwede", "maaari", "magkano", "ano", "sino", "saan",
    "kailan", "bakit", "paano", "meron", "mayroon", "wala", "alam", "malaman",
    "salamat", "kamusta", "kumusta", "magandang", "araw", "umaga", "hapon", "gabi",
    "paki", "tulungan", "tanong", "kuha", "kumuha", "bayad", "magbayad", "buhay",
    "pamilya", "asawa", "anak", "nanay", "tatay", "magulang", "kapatid", "bahay",
    "seguro", "proteksyon", "polisa", "hulog", "benepisyo", "taon", "buwan", "bawat",
    "kada", "milyon", "libo", "medyo", "masyado", "sobra", "mataas", "mababa", "mahal",
    "mura", "edad", "anyos", "ngayon", "kasalukuyan", "hawak", "maaasahan", "impormasyon",
    "ikonekta", "tunay", "ahente", "malugi", "kailangan", "magtanong"
}

# English common tokens
ENGLISH_STOPWORDS = {
    "the", "is", "at", "which", "on", "a", "an", "and", "or", "in", "to", "for",
    "with", "about", "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "from", "up", "down", "of", "off", "over", "under",
    "again", "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "any", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "can", "will", "just", "should", "now", "i", "you", "he", "she", "it", "we", "they",
    "my", "your", "his", "her", "its", "our", "their", "want", "know", "much", "hello",
    "would", "like", "apply", "insurance", "policy", "premium", "coverage", "life",
    "term", "whole", "rider", "lapse", "beneficiary", "bank", "referral", "bdo", "bpi",
    "bake", "cookies", "chocolate", "chip", "crypto", "bitcoin", "weather", "account",
    "budget", "expensive", "afford", "human", "representative", "agent", "advisor"
}

# Required Sector Terminology (Life Insurance & Bancassurance)
REQUIRED_INSURANCE_TERMINOLOGY = {
    "premium": {
        "en": "premium",
        "fil": "hulog o bayad sa insurance",
        "description": "Recurring or lump-sum payment required to maintain insurance coverage."
    },
    "policy": {
        "en": "policy",
        "fil": "polisa o kontrata ng seguro",
        "description": "The legal contract outlining terms, benefits, and conditions."
    },
    "beneficiary": {
        "en": "beneficiary",
        "fil": "benepisyaryo / tatanggap ng benepisyo",
        "description": "Individual(s) entitled to receive the death benefit proceeds."
    },
    "rider": {
        "en": "rider",
        "fil": "karagdagang benepisyo o add-on",
        "description": "Supplemental amendment adding extra benefits such as critical illness or accident."
    },
    "lapse": {
        "en": "lapse",
        "fil": "pagka-paso o paghinto ng bisa",
        "description": "Termination of policy coverage resulting from non-payment of premiums past grace period."
    },
    "coverage": {
        "en": "coverage",
        "fil": "saklaw o halaga ng proteksyon",
        "description": "The total financial protection or face amount payable."
    },
    "bank referral": {
        "en": "bank referral",
        "fil": "endorso mula sa bangko / bancassurance",
        "description": "Referral partnership with universal banks (e.g. BDO, BPI, Metrobank, Security Bank)."
    }
}


class LanguageDetectionResult(BaseModel):
    """Structured result of natural language and code-switching identification."""
    language: str = Field(..., description="'en', 'fil', or 'taglish'")
    code_switch: bool = Field(False, description="True if Tagalog-English code switching is present")
    filipino_token_ratio: float = Field(0.0, description="Ratio of Filipino lexical tokens")
    english_token_ratio: float = Field(0.0, description="Ratio of English lexical tokens")
    detected_markers: List[str] = Field(default_factory=list, description="Filipino markers identified")
    insurance_terms_found: List[str] = Field(default_factory=list, description="Domain terminology found")
    confidence: float = Field(1.0, description="Confidence score between 0.0 and 1.0")


class PhilippinesLocaleEngine:
    """
    Handles natural language detection, code-switching analysis, and terminology
    extraction for the Philippine market without prior machine translation.
    """

    def __init__(self):
        self.filipino_markers = FILIPINO_MARKERS
        self.insurance_terms = REQUIRED_INSURANCE_TERMINOLOGY

    def detect_language(self, text: str) -> LanguageDetectionResult:
        """
        Analyzes an utterance directly to determine whether it is English, Filipino,
        or Taglish (code-switched), detecting honorifics and Filipino grammatical roots.
        """
        clean_text = text.lower().strip()
        tokens = re.findall(r"\b[a-zA-ZñÑáéíóúÁÉÍÓÚ'-]+\b", clean_text)
        
        if not tokens:
            return LanguageDetectionResult(
                language="en",
                code_switch=False,
                confidence=0.5
            )

        fil_count = 0
        en_count = 0
        detected_markers = []
        
        for tok in tokens:
            is_fil = (
                tok in self.filipino_markers
                or (tok.startswith(("nag", "mag", "pag", "paki")) and len(tok) > 4)
            )

            is_en = (
                not is_fil
                and (
                    tok in ENGLISH_STOPWORDS
                    or tok.endswith("ing")
                    or tok.endswith("tion")
                    or tok.endswith("ment")
                    or tok in ["apply", "insurance", "policy", "premium", "coverage", "cookies", "bake", "chocolate", "chip", "life", "term"]
                )
            )

            if is_fil:
                fil_count += 1
                if tok in self.filipino_markers:
                    detected_markers.append(tok)
            elif is_en:
                en_count += 1

        # Check domain insurance terms
        terms_found = []
        for term in self.insurance_terms.keys():
            if term in clean_text:
                terms_found.append(term)

        total_tokens = fil_count + en_count
        fil_ratio = fil_count / total_tokens if total_tokens else 0.0
        en_ratio = en_count / total_tokens if total_tokens else 0.0

        # Classification logic:
        # 1. Pure English: No Filipino markers, mostly English words
        if fil_count == 0:
            lang = "en"
            is_code_switch = False
        # 2. Taglish (Code-switching): Filipino markers present AND English tokens present
        elif en_count > 0:
            lang = "taglish"
            is_code_switch = True
        # 3. Pure Filipino: Filipino words and zero English tokens
        else:
            lang = "fil"
            is_code_switch = False

        confidence = 0.95 if (fil_count > 1 or en_count > 1) else 0.80

        return LanguageDetectionResult(
            language=lang,
            code_switch=is_code_switch,
            filipino_token_ratio=round(fil_ratio, 3),
            english_token_ratio=round(en_ratio, 3),
            detected_markers=list(set(detected_markers)),
            insurance_terms_found=terms_found,
            confidence=confidence
        )

    def extract_insurance_terms(self, text: str) -> Dict[str, Any]:
        """Extracts any life insurance / bancassurance terminology mentioned."""
        clean_text = text.lower()
        matched = {}
        for term, meta in self.insurance_terms.items():
            if re.search(rf"\b{re.escape(term)}\b", clean_text):
                matched[term] = meta
        return matched


ph_locale = PhilippinesLocaleEngine()
