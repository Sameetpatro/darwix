import re
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field


class PhilippinesInsuranceProfile(BaseModel):
    """Structured qualification state for life insurance and bancassurance."""
    applicant_name: Optional[str] = Field(None, description="Borrower / Insured full name")
    age: Optional[int] = Field(None, description="Age in years (18-65 standard)")
    monthly_budget: Optional[float] = Field(None, description="Affordable monthly premium budget in PHP")
    target_coverage: Optional[float] = Field(None, description="Desired face amount protection in PHP")
    insurance_type: Optional[str] = Field(None, description="Term Life, Whole Life, VUL, or Critical Illness")
    beneficiary_relation: Optional[str] = Field(None, description="Designated beneficiary (e.g. spouse, children, parents)")
    health_declaration: Optional[str] = Field(None, description="Non-smoker / healthy or pre-existing conditions")
    bank_partner: Optional[str] = Field(None, description="Bancassurance partner bank (BDO, BPI, Metrobank, Security Bank)")

    def get_missing_fields(self) -> List[str]:
        """Returns ordered list of uncollected critical qualification slots."""
        required_order = [
            "age",
            "target_coverage",
            "monthly_budget",
            "beneficiary_relation",
            "bank_partner"
        ]
        return [f for f in required_order if getattr(self, f) is None]

    def is_complete(self) -> bool:
        """Returns True if the essential underwriting criteria have been gathered."""
        return len(self.get_missing_fields()) == 0


class PhilippinesQualificationEngine:
    """
    Extracts life insurance qualification entities from English, Filipino,
    and Taglish conversational utterances, generating culturally natural prompts.
    """

    def extract_slots(self, text: str, profile: PhilippinesInsuranceProfile) -> Tuple[PhilippinesInsuranceProfile, Dict[str, Any]]:
        clean = text.lower().strip()
        updated = profile.model_copy()
        extracted_this_turn = {}

        # 1. Age extraction (e.g., '32 anyos', 'im 32', '35 years old', 'turning 28')
        if updated.age is None:
            age_match = re.search(r"\b(?:i am|i'm|ako ay|nasa|turning|edad|edad na|age\s+is)?\s*(\d{2})\s*(?:anyos|years?\s+old|yrs?\s+old)?\b", clean)
            if age_match:
                val = int(age_match.group(1))
                if 18 <= val <= 75:
                    updated.age = val
                    extracted_this_turn["age"] = val

        # 2. Target Coverage extraction (e.g., 'isang milyon', '1 million', '₱2,000,000', '500k', '2M')
        if updated.target_coverage is None:
            if re.search(r"\b(?:isang\s+milyon|1\s*(?:m|million|milyon)|₱?\s*1,?000,?000)\b", clean):
                updated.target_coverage = 1000000.0
                extracted_this_turn["target_coverage"] = 1000000.0
            elif re.search(r"\b(?:dalawang\s+milyon|2\s*(?:m|million|milyon)|₱?\s*2,?000,?000)\b", clean):
                updated.target_coverage = 2000000.0
                extracted_this_turn["target_coverage"] = 2000000.0
            elif re.search(r"\b(?:limang\s+milyon|5\s*(?:m|million|milyon)|₱?\s*5,?000,?000)\b", clean):
                updated.target_coverage = 5000000.0
                extracted_this_turn["target_coverage"] = 5000000.0
            elif re.search(r"\b(?:tatlong\s+milyon|3\s*(?:m|million|milyon)|₱?\s*3,?000,?000)\b", clean):
                updated.target_coverage = 3000000.0
                extracted_this_turn["target_coverage"] = 3000000.0
            elif re.search(r"\b(?:500k|500,?000|kalahating\s+milyon)\b", clean):
                updated.target_coverage = 500000.0
                extracted_this_turn["target_coverage"] = 500000.0

        # 3. Monthly Budget extraction (e.g., '2,500 monthly', 'mga 2k kada buwan', '₱1,500')
        if updated.monthly_budget is None:
            # Match formats like '₱2,500', '2500 per month', '3k a month', '1500 kada buwan'
            budget_match = re.search(r"(?:₱|\bphp\b)?\s*(\d{1,2}(?:,\d{3})*|\d+k?)\s*(?:pesos?|bawat\s+buwan|kada\s+buwan|buwan-buwan|monthly|per\s+month|a\s+month)?", clean)
            # Make sure it's not the coverage amount (usually smaller than 50,000 for monthly budget)
            if budget_match:
                raw_val = budget_match.group(1).replace(",", "")
                if "k" in raw_val:
                    num_val = float(raw_val.replace("k", "")) * 1000
                else:
                    num_val = float(raw_val) if raw_val.isdigit() else 0.0
                
                if 500 <= num_val <= 50000:
                    updated.monthly_budget = num_val
                    extracted_this_turn["monthly_budget"] = num_val

        # 4. Beneficiary Relation (e.g., 'asawa at dalawang anak', 'sa nanay ko', 'wife and children', 'my parents')
        if updated.beneficiary_relation is None:
            if re.search(r"\b(?:asawa|misis|mister|husband|wife|spouse)\b", clean):
                updated.beneficiary_relation = "Spouse and Family"
                extracted_this_turn["beneficiary_relation"] = updated.beneficiary_relation
            elif re.search(r"\b(?:anak|kids|children|son|daughter)\b", clean):
                updated.beneficiary_relation = "Children"
                extracted_this_turn["beneficiary_relation"] = updated.beneficiary_relation
            elif re.search(r"\b(?:nanay|tatay|magulang|ina|ama|parents|mother|father)\b", clean):
                updated.beneficiary_relation = "Parents"
                extracted_this_turn["beneficiary_relation"] = updated.beneficiary_relation
            elif re.search(r"\b(?:kapatid|sibling|brother|sister)\b", clean):
                updated.beneficiary_relation = "Siblings"
                extracted_this_turn["beneficiary_relation"] = updated.beneficiary_relation

        # 5. Bank Partner (Bancassurance referral)
        if updated.bank_partner is None:
            if "bdo" in clean:
                updated.bank_partner = "BDO Unibank"
                extracted_this_turn["bank_partner"] = "BDO Unibank"
            elif "bpi" in clean:
                updated.bank_partner = "Bank of the Philippine Islands (BPI)"
                extracted_this_turn["bank_partner"] = "Bank of the Philippine Islands (BPI)"
            elif "metrobank" in clean:
                updated.bank_partner = "Metrobank"
                extracted_this_turn["bank_partner"] = "Metrobank"
            elif "security bank" in clean:
                updated.bank_partner = "Security Bank"
                extracted_this_turn["bank_partner"] = "Security Bank"
            elif re.search(r"\b(?:walang\s+bank|wala\s+po|none|no\s+bank)\b", clean):
                updated.bank_partner = "Direct / Non-Bank"
                extracted_this_turn["bank_partner"] = "Direct / Non-Bank"

        # 6. Insurance Type preference (Term vs Whole Life vs VUL)
        if updated.insurance_type is None:
            if re.search(r"\b(?:term\s+life|term|secureterm|pure\s+protection)\b", clean):
                updated.insurance_type = "Darwix SecureTerm (Term Life)"
                extracted_this_turn["insurance_type"] = updated.insurance_type
            elif re.search(r"\b(?:whole\s+life|lifeheritage|lifetime|pang-habangbuhay)\b", clean):
                updated.insurance_type = "Darwix LifeHeritage (Whole Life)"
                extracted_this_turn["insurance_type"] = updated.insurance_type
            elif re.search(r"\b(?:vul|unit-linked|investment|investshield)\b", clean):
                updated.insurance_type = "Darwix InvestShield (VUL)"
                extracted_this_turn["insurance_type"] = updated.insurance_type

        # 7. Health / Smoker status
        if updated.health_declaration is None:
            if re.search(r"\b(?:non-smoker|hindi\s+naninigarilyo|hindi\s+nagyo-yosi|healthy|walang\s+sakit)\b", clean):
                updated.health_declaration = "Standard Non-Smoker (Healthy)"
                extracted_this_turn["health_declaration"] = updated.health_declaration
            elif re.search(r"\b(?:smoker|naninigarilyo|nagyo-yosi)\b", clean):
                updated.health_declaration = "Smoker"
                extracted_this_turn["health_declaration"] = updated.health_declaration

        return updated, extracted_this_turn

    def get_next_question(self, profile: PhilippinesInsuranceProfile, language: str = "taglish") -> str:
        """
        Generates the next conversational qualification question in the requested language
        (Taglish, Filipino, or English) asking ONLY for missing fields.
        """
        missing = profile.get_missing_fields()
        if not missing:
            return self.get_qualification_summary(profile, language)

        next_slot = missing[0]

        prompts = {
            "age": {
                "taglish": "Ilang taon na po kayo ngayon para ma-compute natin ang accurate rate?",
                "fil": "Ilang taon na po kayo sa kasalukuyan upang matiyak ang tamang halaga ng premium?",
                "en": "May I know your current age so we can calculate your personalized insurance rate?"
            },
            "target_coverage": {
                "taglish": "Magkano po ang nais ninyong coverage o halaga ng proteksyon para sa inyong pamilya, halimbawa ₱1 Million or ₱2 Million?",
                "fil": "Magkano po ang halaga ng proteksyon o coverage na nais ninyo para sa inyong pamilya, tulad ng ₱1 Million o higit pa?",
                "en": "What face amount or coverage protection are you looking for, such as ₱1 Million or ₱2 Million?"
            },
            "monthly_budget": {
                "taglish": "Magkano po ang komportableng monthly budget ninyo para sa insurance premium, halimbawa ₱1,500 or ₱2,500 bawat buwan?",
                "fil": "Magkano po ang inyong komportableng buwanang badyet para sa premium ng inyong seguro?",
                "en": "What is your comfortable monthly budget for your insurance premium, like ₱1,500 or ₱2,500 per month?"
            },
            "beneficiary_relation": {
                "taglish": "Sino po ang nais ninyong maging primary beneficiary—ang inyong asawa po ba, mga anak, o mga magulang?",
                "fil": "Sino po ang inyong itatalagang pangunahing benepisyaryo—ang inyong asawa, mga anak, o mga magulang?",
                "en": "Who would you like to designate as your primary beneficiary—your spouse, children, or parents?"
            },
            "bank_partner": {
                "taglish": "May existing bank account po ba kayo sa aming Bancassurance partner banks tulad ng BDO, BPI, Metrobank, o Security Bank para sa auto-debit discount?",
                "fil": "Kayo po ba ay mayroong bank account sa aming partner banks tulad ng BDO, BPI, Metrobank, o Security Bank upang makakuha ng discount?",
                "en": "Do you hold an account with any of our Bancassurance partner banks such as BDO, BPI, Metrobank, or Security Bank to enjoy auto-debit privileges?"
            }
        }

        lang_key = language if language in ["taglish", "fil", "en"] else "taglish"
        return prompts.get(next_slot, {}).get(lang_key, prompts[next_slot]["taglish"])

    def get_qualification_summary(self, profile: PhilippinesInsuranceProfile, language: str = "taglish") -> str:
        """Generates a warm, structured pre-qualification proposal."""
        cov_str = f"₱{profile.target_coverage:,.0f}" if profile.target_coverage else "₱1,000,000"
        bud_str = f"₱{profile.monthly_budget:,.0f}" if profile.monthly_budget else "₱1,500"
        bank_str = profile.bank_partner or "Partner Bank"
        ben_str = profile.beneficiary_relation or "Inyong Pamilya"

        if language == "fil":
            return (
                f"Maraming salamat po! Batay sa inyong edad ({profile.age or 30} taong gulang) at buwanang badyet na {bud_str}, "
                f"lubos po naming inirerekomenda ang Darwix SecureTerm na may {cov_str} coverage para kay {ben_str}. "
                f"Dahil kayo ay may bank relationship sa {bank_str}, kwalipikado po kayo sa 5% auto-debit premium rebate. "
                f"Gusto niyo po bang ipasa ko na ito sa ating Financial Advisor para ma-finalize ang inyong opisyal na quotation?"
            )
        elif language == "en":
            return (
                f"Thank you very much! Based on your age ({profile.age or 30}) and monthly budget of {bud_str}, "
                f"we recommend the Darwix SecureTerm plan with {cov_str} coverage protecting {ben_str}. "
                f"Through your relationship with {bank_str}, you also qualify for an express non-medical limit and a 5% auto-debit rebate. "
                f"Would you like me to connect you with our licensed Financial Advisor to finalize your official policy application?"
            )
        else: # taglish
            return (
                f"Maraming salamat po! Based sa inyong details (Age: {profile.age or 30} years old, Budget: {bud_str} per month), "
                f"swak na swak po sa inyo ang Darwix SecureTerm with {cov_str} protection para kay {ben_str}. "
                f"Dahil po sa inyong bank account sa {bank_str}, may 5% rebate po kayo on auto-debit! "
                f"Gusto niyo po bang i-connect ko na kayo sa ating licensed Financial Advisor para ma-send ang formal quotation?"
            )


ph_qualification_engine = PhilippinesQualificationEngine()
