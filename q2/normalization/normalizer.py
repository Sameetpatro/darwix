import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from q2.models.knowledge_record import NormalizedEntities


PRODUCT_SYNONYMS = {
    "Term Loan": [
        "term loan", "commercial term loan", "fixed term loan", "prime commercial term",
        "prime commercial", "standard commercial"
    ],
    "Line of Credit": [
        "line of credit", "revolving line of credit", "business line of credit",
        "revolving credit facility", "loc"
    ],
    "Equipment Financing": [
        "equipment financing", "machinery leasing", "equipment leasing",
        "heavy machinery", "machinery lease", "hardware leasing"
    ],
    "SBA 7(a) Loan": [
        "sba 7a", "sba 7(a)", "sba prime guarantee", "sba loan",
        "small business administration 7(a)", "sba guarantee"
    ],
    "Working Capital Loan": [
        "working capital loan", "alternative working capital", "short-term working capital",
        "working capital facility", "working capital"
    ],
    "Invoice Factoring": [
        "invoice factoring", "accounts receivable financing", "receivables factoring",
        "ar financing"
    ],
}

ENTITY_TYPE_SYNONYMS = {
    "LLC": ["llc", "limited liability company", "limited liability co"],
    "C-Corp": ["c-corp", "c corp", "c corporation", "regular corporation"],
    "S-Corp": ["s-corp", "s corp", "s corporation"],
    "Sole Proprietorship": ["sole proprietorship", "sole prop", "individual owner"],
    "Partnership": ["partnership", "general partnership", "limited partnership", "llp"],
}


class EntityNormalizer:
    """
    Standardizes commercial lending entities, financial constraints,
    operating history, currency figures, and dates into structured schemas.
    """

    def normalize(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> NormalizedEntities:
        entities = NormalizedEntities()
        if not text:
            return entities

        # 1. Product Identification
        entities.loan_products = self.extract_products(text)

        # 2. Entity Types
        entities.entity_types = self.extract_entity_types(text)

        # 3. Operating History (Time in Business)
        months, display = self.extract_operating_history(text)
        if months is not None:
            entities.time_in_business_months = months
            entities.time_in_business_display = display

        # 4. Revenue Requirements
        min_rev = self.extract_min_revenue(text)
        if min_rev is not None:
            entities.min_revenue_monthly_usd = min_rev

        # 5. Credit Score Requirements
        min_cs = self.extract_credit_score(text)
        if min_cs is not None:
            entities.min_credit_score = min_cs

        # 6. Loan Facility Amount Range
        min_amt, max_amt = self.extract_loan_amounts(text)
        if min_amt is not None:
            entities.min_loan_amount_usd = min_amt
        if max_amt is not None:
            entities.max_loan_amount_usd = max_amt

        # 7. APR / Interest Rates
        min_apr, max_apr = self.extract_apr_range(text)
        if min_apr is not None:
            entities.min_apr = min_apr
        if max_apr is not None:
            entities.max_apr = max_apr

        # 8. Repayment Frequency
        entities.repayment_frequency = self.extract_repayment_frequency(text)

        # 9. Prepayment Penalty
        entities.prepayment_penalty_allowed = self.extract_prepayment_penalty(text)

        # 10. Dates (ISO 8601)
        entities.normalized_dates = self.extract_dates(text)

        return entities

    def extract_products(self, text: str) -> List[str]:
        found = []
        lower = text.lower()
        for canonical, syns in PRODUCT_SYNONYMS.items():
            for syn in syns:
                if re.search(r"\b" + re.escape(syn) + r"\b", lower):
                    found.append(canonical)
                    break
        return found

    def extract_entity_types(self, text: str) -> List[str]:
        found = []
        lower = text.lower()
        for canonical, syns in ENTITY_TYPE_SYNONYMS.items():
            for syn in syns:
                if re.search(r"\b" + re.escape(syn) + r"\b", lower):
                    found.append(canonical)
                    break
        return found

    def extract_operating_history(self, text: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Extracts minimum required months of operating history.
        e.g. '6 months', '12 to 24 months', '2 years', '3 yrs'
        """
        # Look for phrases around operating history, time in business, active operations
        # Pattern 1: X to Y months or X months
        month_match = re.search(
            r"(?:operating\s+history|time\s+in\s+business|months_in_business|active\s+operations|business\s+age).*?"
            r"(\d+)(?:\s*(?:to|-)\s*(\d+))?\s*(?:months?|mos?\b)",
            text,
            re.IGNORECASE,
        )
        if month_match:
            val = int(month_match.group(1))
            return val, f"{val} months ({round(val / 12.0, 1)} years)"

        # Pattern 2: X years / yrs
        year_match = re.search(
            r"(?:operating\s+history|time\s+in\s+business|active\s+operations|business\s+age).*?"
            r"(\d+(?:\.\d+)?)(?:\s*(?:to|-)\s*(\d+(?:\.\d+)?))?\s*(?:years?|yrs?\b)",
            text,
            re.IGNORECASE,
        )
        if year_match:
            years = float(year_match.group(1))
            months = int(round(years * 12))
            return months, f"{months} months ({years} years)"

        # Fallback: check table format or direct mention like 'min_months_in_business: 24'
        direct_match = re.search(r"min_months_in_business[:\s=]+(\d+)", text, re.IGNORECASE)
        if direct_match:
            val = int(direct_match.group(1))
            return val, f"{val} months ({round(val / 12.0, 1)} years)"

        # Fallback 2: 'at least 6 months', 'minimum of 12 months'
        at_least_match = re.search(r"(?:at\s+least|minimum\s+of)\s+(\d+)\s*(?:months?|mos?\b)", text, re.IGNORECASE)
        if at_least_match:
            val = int(at_least_match.group(1))
            return val, f"{val} months ({round(val / 12.0, 1)} years)"

        return None, None

    def extract_min_revenue(self, text: str) -> Optional[float]:
        """
        Extracts minimum required monthly gross revenue in USD.
        """
        # CSV format: min_monthly_revenue: 30000
        csv_match = re.search(r"min_monthly_revenue[:\s=]+(\d+)", text, re.IGNORECASE)
        if csv_match:
            return float(csv_match.group(1))

        # Text format: minimum average monthly gross revenues of $10,000 / $10k
        rev_match = re.search(
            r"(?:monthly\s+(?:gross\s+)?revenue|gross\s+revenues).*?"
            r"(?:\$|\bUSD\s*)?(\d{1,3}(?:,\d{3})+|\d+)(?:\s*k|\s*thousand)?",
            text,
            re.IGNORECASE,
        )
        if rev_match:
            raw_str = rev_match.group(1).replace(",", "")
            val = float(raw_str)
            if "k" in rev_match.group(0).lower() or "thousand" in rev_match.group(0).lower():
                val *= 1000
            if val > 100:  # Guard against trivial percentages or ratios
                return val

        return None

    def extract_credit_score(self, text: str) -> Optional[int]:
        """
        Extracts minimum required credit score (FICO).
        """
        # CSV / structured: min_credit_score: 680
        csv_match = re.search(r"min_credit_score[:\s=]+(\d{3})", text, re.IGNORECASE)
        if csv_match:
            return int(csv_match.group(1))

        # Text: credit score of at least 620 / min 680 FICO
        cs_match = re.search(
            r"(?:credit\s+score|fico).*?(\b[5-8]\d{2}\b)",
            text,
            re.IGNORECASE,
        )
        if cs_match:
            return int(cs_match.group(1))

        return None

    def extract_loan_amounts(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Extracts loan amount facility range: (min_usd, max_usd).
        e.g. '$25,000 up to $2,000,000' or '$10,000 - $500,000'
        """
        # Pattern: $X to $Y or $X up to $Y
        range_match = re.search(
            r"(?:facility\s+range|loan\s+amount|amount).*?"
            r"(?:\$|\bUSD\s*)?(\d{1,3}(?:,\d{3})+|\d+)\s*(?:up\s+to|to|-)\s*(?:\$|\bUSD\s*)?(\d{1,3}(?:,\d{3})+|\d+)",
            text,
            re.IGNORECASE,
        )
        if range_match:
            min_val = float(range_match.group(1).replace(",", ""))
            max_val = float(range_match.group(2).replace(",", ""))
            return min_val, max_val

        # Single max amount mention: e.g. Max Amount: $1,000,000 or Construction Machinery $1,000,000
        max_match = re.search(r"(?:max\s+amount|maximum\s+loan).*?(?:\$|\bUSD\s*)?(\d{1,3}(?:,\d{3})+)", text, re.IGNORECASE)
        if max_match:
            max_val = float(max_match.group(1).replace(",", ""))
            return None, max_val

        return None, None

    def extract_apr_range(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Extracts min and max APR rates in percent.
        e.g. '5.99% to 10.99%' or 'Starting Rates: 5.99% APR'
        """
        # CSV / direct: min_apr: 5.99%, max_apr: 10.99%
        direct_match = re.search(r"min_apr[:\s=]+([\d\.]+)%.*?max_apr[:\s=]+([\d\.]+)%", text, re.IGNORECASE)
        if direct_match:
            return float(direct_match.group(1)), float(direct_match.group(2))

        # Range in text: 11.00% to 17.99%
        range_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*%", text)
        if range_match:
            return float(range_match.group(1)), float(range_match.group(2))

        # Single starting rate: 'starting at 5.99% APR' or '5.99% APR'
        single_match = re.search(r"(?:starting\s+rates?|starting\s+at|rates?\s+start\s+at)?\s*(\d+(?:\.\d+)?)\s*%\s*(?:apr)?", text, re.IGNORECASE)
        if single_match:
            val = float(single_match.group(1))
            if 1.0 <= val <= 99.0:
                return val, None

        return None, None

    def extract_repayment_frequency(self, text: str) -> Optional[str]:
        lower = text.lower()
        if "repayment_frequency" in lower:
            # Extract from CSV / line
            match = re.search(r"repayment_frequency[:\s=]+([A-Za-z\s/-]+)", text, re.IGNORECASE)
            if match:
                raw = match.group(1).strip()
                # Normalize
                if "daily" in raw.lower():
                    return "Daily"
                if "weekly" in raw.lower():
                    return "Weekly"
                if "bi-weekly" in raw.lower():
                    return "Bi-Weekly"
                if "monthly" in raw.lower():
                    return "Monthly"
                return raw

        if "monthly ach" in lower or "monthly repayment" in lower:
            return "Monthly"
        if "bi-weekly" in lower:
            return "Bi-Weekly"
        if "weekly" in lower:
            return "Weekly"
        if "daily" in lower:
            return "Daily"

        return None

    def extract_prepayment_penalty(self, text: str) -> Optional[bool]:
        lower = text.lower()
        if "zero prepayment penalties" in lower or "no prepayment penalty" in lower or "zero penalty" in lower or "without penalty" in lower:
            return False
        if "prepayment penalty applies" in lower or "prepayment penalty of" in lower:
            return True
        return None

    def extract_dates(self, text: str) -> List[str]:
        """
        Parses dates and returns ISO 8601 strings (YYYY-MM-DD).
        """
        iso_dates = []

        # 1. YYYY-MM-DD
        for m in re.finditer(r"\b(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b", text):
            iso_dates.append(m.group(0))

        # 2. MM/DD/YYYY
        for m in re.finditer(r"\b(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/(20\d{2})\b", text):
            try:
                dt = datetime.strptime(m.group(0), "%m/%d/%Y" if len(m.group(1)) == 2 else "%-m/%-d/%Y")
                iso_dates.append(dt.strftime("%Y-%m-%d"))
            except Exception:
                pass

        # 3. Month Name Day, Year (e.g. January 15, 2026)
        months_pat = (
            r"(?i)\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
            r"([0-2]?[0-9]|3[01]),?\s+(20\d{2})\b"
        )
        for m in re.finditer(months_pat, text):
            month_str, day_str, year_str = m.group(1), m.group(2), m.group(3)
            try:
                dt = datetime.strptime(f"{month_str} {day_str} {year_str}", "%B %d %Y")
                iso_dates.append(dt.strftime("%Y-%m-%d"))
            except Exception:
                pass

        return list(set(iso_dates))


entity_normalizer = EntityNormalizer()
