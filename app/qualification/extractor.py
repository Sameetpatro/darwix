import re
from typing import Dict, Any, Optional
from app.logging_config import logger


def parse_dollar_amount(text: str) -> Optional[float]:
    """Parses verbal and written currency expressions like '$50k', '50,000', '1.5 million', '75 thousand'."""
    text = text.lower().replace(",", "")

    # Match '$50k' or '50k' or '50k dollars'
    m_k = re.search(r"\$?(\d+(\.\d+)?)\s*(k|thousand)\b", text)
    if m_k:
        return float(m_k.group(1)) * 1000.0

    # Match '$1.5m' or '1.5 million'
    m_m = re.search(r"\$?(\d+(\.\d+)?)\s*(m|million)\b", text)
    if m_m:
        return float(m_m.group(1)) * 1000000.0

    # Match standard dollar figures like '$50000' or '50000 dollars'
    m_std = re.search(r"\$\s*(\d+(\.\d+)?)", text)
    if m_std:
        return float(m_std.group(1))

    m_words = re.search(r"\b(\d{3,9})\b\s*(dollars)?", text)
    if m_words:
        return float(m_words.group(1))

    return None


def parse_business_age_months(text: str) -> Optional[int]:
    """Parses expressions of business age like '3 years', '18 months', '2 and a half years', '6 months'."""
    lowered = text.lower()

    # Years matching
    m_yr = re.search(r"(\d+(\.\d+)?)\s*(year|yr)s?", lowered)
    if m_yr:
        return int(float(m_yr.group(1)) * 12)

    # Worded numbers for years
    word_to_num = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }
    for word, val in word_to_num.items():
        if f"{word} year" in lowered or f"{word} yr" in lowered:
            return val * 12

    # Months matching
    m_mo = re.search(r"(\d+)\s*(month|mo)s?", lowered)
    if m_mo:
        return int(m_mo.group(1))

    return None


def format_company_name(name: str) -> str:
    title_cased = name.strip().title()
    for suffix in ["LLC", "LLP", "PLLC", "INC", "CORP", "LTD", "DBA", "PC"]:
        title_cased = re.sub(rf"\b{suffix}\b", suffix, title_cased, flags=re.IGNORECASE)
    return title_cased


def extract_qualification_data(text: str, current_missing: Optional[list] = None) -> Dict[str, Any]:
    """
    Extracts business-loan qualification fields from caller utterance.
    Handles multiple fields volunteered at once.
    """
    extracted: Dict[str, Any] = {}
    lowered = text.lower().strip()

    # 1. Monthly Revenue
    if any(k in lowered for k in ["revenue", "monthly", "make about", "making about", "earn", "gross", "bring in"]):
        amt = parse_dollar_amount(text)
        if amt:
            extracted["monthly_revenue"] = amt
            extracted["monthly_revenue_raw"] = f"${amt:,.0f}"

    # 2. Requested Loan Amount
    if any(k in lowered for k in ["need", "looking for", "borrow", "request", "loan of", "want", "seeking"]):
        amt = parse_dollar_amount(text)
        if amt:
            # If monthly revenue was also extracted, distinguish if there are two amounts
            amounts = re.findall(r"\$?\d+(?:,\d+)*(?:\.\d+)?\s*(?:k|thousand|million|m)?", lowered)
            if len(amounts) >= 2 and "revenue" in lowered:
                pass  # Handled in multi-amount parsing
            else:
                extracted["requested_amount"] = amt
                extracted["requested_amount_raw"] = f"${amt:,.0f}"

    # Standalone dollar amount if requested_amount or monthly_revenue is currently the pending question
    if current_missing and len(extracted) == 0:
        amt = parse_dollar_amount(text)
        if amt:
            if current_missing[0] == "monthly_revenue":
                extracted["monthly_revenue"] = amt
                extracted["monthly_revenue_raw"] = f"${amt:,.0f}"
            elif current_missing[0] == "requested_amount":
                extracted["requested_amount"] = amt
                extracted["requested_amount_raw"] = f"${amt:,.0f}"

    # 3. Customer Name
    m_name = re.search(r"\b(?:my name is|i am|this is|i'm|call me)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)", text, re.IGNORECASE)
    if m_name:
        candidate = m_name.group(1).strip()
        if candidate.lower() not in ["alex", "vani", "darwix", "calling", "interested", "looking", "here", "ready"]:
            extracted["customer_name"] = candidate
    elif current_missing and current_missing[0] == "customer_name":
        words = text.strip().split()
        if 1 <= len(words) <= 3 and not any(w in lowered for w in ["yes", "no", "loan", "help", "hello"]):
            extracted["customer_name"] = text.strip().title()

    # 4. Business Name
    # A. Explicit phrase triggers (e.g. 'my business is Apex Horizon.', 'I own Summit Logistics LLC in Dallas')
    m_biz = re.search(
        r"\b(?:my business is|company is|business is|company name is|business name is|i own|i run|called|named|from)\s+([A-Za-z0-9\s&'-]+?)(?:[.,]|\s+(?:in|located|and\s+we|we\s+need|which)|\s*$)",
        text,
        re.IGNORECASE,
    )
    if m_biz:
        candidate = m_biz.group(1).strip().strip(".,")
        if len(candidate) > 2 and candidate.lower() not in ["a loan", "home", "here", "texas", "california", "florida"]:
            extracted["business_name"] = format_company_name(candidate)

    # B. Suffix based matching (e.g. Summit Logistics LLC, City Bakery) if not already extracted
    if "business_name" not in extracted:
        m_suffix = re.search(
            r"\b([A-Z][A-Za-z0-9\s&'-]+?\b(?:LLC|Inc|Corp|Bakery|Logistics|Solutions|Services|Store|Cafe|Restaurant|Consulting|Group|Enterprises))\b",
            text,
            re.IGNORECASE,
        )
        if m_suffix:
            candidate = m_suffix.group(1).strip()
            if candidate.lower() not in ["business entity", "llc", "corp"]:
                extracted["business_name"] = format_company_name(candidate)

    if "business_name" not in extracted and current_missing and current_missing[0] == "business_name":
        if len(text.strip().split()) <= 5 and not any(w in lowered for w in ["yes", "no", "loan"]):
            extracted["business_name"] = format_company_name(text)

    # 5. Business Type / Entity / Industry
    entity_types = ["llc", "c-corp", "s-corp", "corporation", "sole proprietorship", "sole proprietor", "partnership", "nonprofit"]
    for et in entity_types:
        if et in lowered:
            extracted["business_type"] = et.upper() if len(et) <= 6 else et.title()
            break

    industries = ["retail", "restaurant", "bakery", "construction", "transportation", "logistics", "healthcare", "medical", "tech", "software", "ecommerce", "manufacturing", "auto repair", "consulting"]
    if "business_type" not in extracted:
        for ind in industries:
            if ind in lowered:
                extracted["business_type"] = f"{ind.title()} Business"
                break
    if "business_type" not in extracted and current_missing and current_missing[0] == "business_type":
        extracted["business_type"] = text.strip().title()

    # 6. Business Age
    months = parse_business_age_months(text)
    if months is not None:
        extracted["business_age_months"] = months
        extracted["business_age_raw"] = f"{months} months ({months/12:.1f} years)" if months >= 12 else f"{months} months"
    elif current_missing and current_missing[0] == "business_age":
        m_num = re.search(r"\b(\d+)\b", text)
        if m_num:
            val = int(m_num.group(1))
            # Assume years if small number (1-30)
            months = val * 12 if val <= 30 else val
            extracted["business_age_months"] = months
            extracted["business_age_raw"] = f"{months} months"

    # 7. Loan Purpose
    purposes = {
        "equipment": ["equipment", "machinery", "truck", "van", "tools", "computer"],
        "working capital": ["working capital", "operating expenses", "cash flow", "day to day", "bills"],
        "inventory": ["inventory", "supplies", "stock", "raw materials"],
        "expansion": ["expansion", "expand", "new location", "second branch", "renovation", "remodel"],
        "payroll": ["payroll", "hiring", "hire staff", "pay employees"],
        "refinancing": ["refinance", "pay off debt", "consolidate"],
    }
    for category, keywords in purposes.items():
        if any(kw in lowered for kw in keywords):
            extracted["loan_purpose"] = category.title()
            break
    if "loan_purpose" not in extracted and current_missing and current_missing[0] == "loan_purpose":
        extracted["loan_purpose"] = text.strip().capitalize()

    # 8. Existing Loans
    if any(k in lowered for k in ["no existing", "no loans", "none", "don't have any", "do not have any", "no debt", "clean slate"]):
        extracted["has_existing_loans"] = False
        extracted["existing_loans_details"] = "None"
    elif any(k in lowered for k in ["yes we have", "have a loan", "sba loan", "line of credit", "existing debt", "current loan", "owe about", "have one"]):
        extracted["has_existing_loans"] = True
        extracted["existing_loans_details"] = text.strip()
    elif current_missing and current_missing[0] == "existing_loans":
        if any(w in lowered for w in ["no", "nope", "zero"]):
            extracted["has_existing_loans"] = False
            extracted["existing_loans_details"] = "None"
        elif any(w in lowered for w in ["yes", "yeah", "we do"]):
            extracted["has_existing_loans"] = True
            extracted["existing_loans_details"] = "Yes"

    # 9. Location (City and State)
    # 9. Location (City and State)
    us_state_names = {
        "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
        "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
        "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
        "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
        "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
        "montana": "MT", "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
        "new mexico": "NM", "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
        "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
        "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
        "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    }

    # Match City + State pattern (e.g. "Dallas, Texas", "in Austin TX", "based in Miami, Florida")
    for state_name, abbrev in us_state_names.items():
        m_city = re.search(rf"\b(?:in|based in|from)\s+([A-Z][a-zA-Z\s]+?)[,\s]+(?:{state_name}|{abbrev})\b", text, re.IGNORECASE)
        if not m_city:
            m_city = re.search(rf"\b([A-Z][a-zA-Z\s]+?),\s*(?:{state_name}|{abbrev})\b", text, re.IGNORECASE)
        if m_city:
            city_name = m_city.group(1).strip().title()
            if city_name.lower() not in ["operating", "business", "years", "do", "we", "located", "our"]:
                extracted["location"] = f"{city_name}, {abbrev}"
                break

    # Match standalone state name (e.g. "based in Texas", "in Florida")
    if "location" not in extracted:
        for state_name, abbrev in us_state_names.items():
            if re.search(rf"\b(?:in|based in|from)\s+{state_name}\b", lowered) or lowered == state_name:
                extracted["location"] = f"{state_name.title()}, {abbrev}"
                break

    if "location" not in extracted and current_missing and current_missing[0] == "location":
        extracted["location"] = text.strip().title()

    if extracted:
        logger.info("[EXTRACTOR] Extracted fields from utterance: %s", list(extracted.keys()))

    return extracted
