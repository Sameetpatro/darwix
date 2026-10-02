import re
from typing import Tuple, Dict, Any


# 1. SSN Pattern: 3-2-4 digits with optional dashes or spaces, with invalid range guard
SSN_PATTERN = re.compile(
    r"\b(?!000|666|9\d{2})(\d{3})[- ]?(?!00)(\d{2})[- ]?(?!0000)(\d{4})\b"
)

# 2. EIN Pattern: 2 digits - 7 digits (often preceded by EIN, Tax ID, FEIN)
EIN_PATTERN = re.compile(
    r"(?i)\b(?:ein|tax\s*id|fein|employer\s*id)?\s*[:#]?\s*(\d{2}-\d{7})\b"
)

# 3. US Phone Pattern
PHONE_PATTERN = re.compile(
    r"\b(?:\+?1[-. ]?)?(?:\(?([2-9]\d{2})\)?[-. ]?)(\d{3})[-. ]?(\d{4})\b"
)

# 4. Email Pattern
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# 5. Routing Number (9 digits preceded by ABA / Routing keywords)
ROUTING_PATTERN = re.compile(
    r"(?i)\b(?:routing(?:\s*number|\s*transit|\s*no\.?|\s*#)?|aba(?:\s*#|\s*number)?)\s*[:#]?\s*([0-9]{9})\b"
)

# 6. Bank Account Number (8 to 17 digits preceded by Account keywords)
BANK_ACCOUNT_PATTERN = re.compile(
    r"(?i)\b(?:account(?:\s*number|\s*no\.?|\s*#)?|acct(?:\s*#|\s*no\.?)?|checking(?:\s*account|\s*#)?)\s*[:#]?\s*([0-9]{8,17})\b"
)

# 7. Person / Guarantor Names with explicit context markers
NAME_CONTEXT_PATTERN = re.compile(
    r"(?i)\b(guarantor|applicant(?:\s*name)?|business\s*owner|prepared\s*by|representative|contact\s*person)\s*[:]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
)


class PIIRedactor:
    """
    Detects and masks Personally Identifiable Information (PII) and sensitive financial data.
    Provides structured audit tracking for compliance.
    """

    def redact(self, text: str) -> Tuple[str, Dict[str, int]]:
        """
        Redacts PII from text and returns (redacted_text, audit_counts).
        """
        if not text:
            return "", {}

        audit: Dict[str, int] = {
            "ssn": 0,
            "ein": 0,
            "phone": 0,
            "email": 0,
            "bank_account": 0,
            "routing_number": 0,
            "person_name": 0,
        }

        redacted = text

        # 1. Routing Number (run before generic numbers)
        def replace_routing(m):
            audit["routing_number"] += 1
            full_match = m.group(0)
            target = m.group(1)
            return full_match.replace(target, "[REDACTED_ROUTING_NUMBER]")

        redacted = ROUTING_PATTERN.sub(replace_routing, redacted)

        # 2. Bank Account Number
        def replace_account(m):
            audit["bank_account"] += 1
            full_match = m.group(0)
            target = m.group(1)
            return full_match.replace(target, "[REDACTED_BANK_ACCOUNT]")

        redacted = BANK_ACCOUNT_PATTERN.sub(replace_account, redacted)

        # 3. Person Names with Context
        def replace_name(m):
            audit["person_name"] += 1
            marker = m.group(1)
            return f"{marker}: [REDACTED_NAME]"

        redacted = NAME_CONTEXT_PATTERN.sub(replace_name, redacted)

        # 4. Email
        def replace_email(m):
            audit["email"] += 1
            return "[REDACTED_EMAIL]"

        redacted = EMAIL_PATTERN.sub(replace_email, redacted)

        # 5. Phone
        def replace_phone(m):
            audit["phone"] += 1
            return "[REDACTED_PHONE]"

        redacted = PHONE_PATTERN.sub(replace_phone, redacted)

        # 6. EIN (handles with or without prefix)
        def replace_ein(m):
            audit["ein"] += 1
            full = m.group(0)
            ein_val = m.group(1)
            return full.replace(ein_val, "[REDACTED_EIN]")

        redacted = EIN_PATTERN.sub(replace_ein, redacted)

        # 7. SSN
        def replace_ssn(m):
            audit["ssn"] += 1
            return "[REDACTED_SSN]"

        redacted = SSN_PATTERN.sub(replace_ssn, redacted)

        # Filter out 0 counts from audit dict
        final_audit = {k: v for k, v in audit.items() if v > 0}

        return redacted, final_audit


pii_redactor = PIIRedactor()
