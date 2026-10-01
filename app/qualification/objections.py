import re
from typing import Optional, Tuple, Dict

# Explicit Human Escalation Patterns
ESCALATION_TRIGGERS = [
    r"\b(speak|talk) (to|with) (a )?(human|person|agent|representative|advisor|specialist|manager|supervisor)\b",
    r"\b(transfer|connect) me\b",
    r"\breal person\b",
    r"\bhuman (assistance|agent|representative)\b",
    r"\bcan i (speak|talk) with someone\b",
    r"\bi need a human\b",
    r"\boperator\b",
]

# Common Loan Objections and standard reassuring responses
OBJECTION_RESPONSES = {
    "interest_rate": {
        "patterns": [
            r"\b(interest rate|rates|apr|cost of capital|expensive)\b",
            r"\bhow much interest\b",
            r"\bwhat (are|is) your rate\b",
        ],
        "response": (
            "Our rates start as low as 6.99% APR depending on your business revenue, time in business, and loan program. "
            "Because we work with multiple tier-one lenders, we always match you with the most competitive rate available."
        ),
    },
    "credit_check": {
        "patterns": [
            r"\b(credit score|credit check|hard pull|soft pull|hurt my credit|bad credit)\b",
            r"\bwill this affect my credit\b",
        ],
        "response": (
            "Good news: our initial qualification uses a soft credit inquiry, so reviewing your options will not impact your credit score at all."
        ),
    },
    "funding_timeline": {
        "patterns": [
            r"\b(how fast|how long|timeline|urgent|immediately|turnaround|same day|quick)\b",
            r"\bhow soon can i get (funds|money|funded|the loan)\b",
        ],
        "response": (
            "Most of our commercial loans can be approved within 24 hours and funded in as little as 1 to 2 business days once basic documents are reviewed."
        ),
    },
    "upfront_fees": {
        "patterns": [
            r"\b(upfront fee|application fee|broker fee|cost to apply|hidden fees)\b",
            r"\bdo you charge (a )?fee\b",
        ],
        "response": (
            "There are absolutely zero upfront application fees or hidden costs to see what you qualify for."
        ),
    },
    "paperwork_burden": {
        "patterns": [
            r"\b(paperwork|documentation|tax returns|financial statements|hassle|too much documentation)\b",
            r"\bhow much paperwork\b",
        ],
        "response": (
            "Our process is streamlined and digital. Usually, all that is needed for initial approval is three to six months of business bank statements."
        ),
    },
}


def detect_escalation_intent(text: str) -> Tuple[bool, Optional[str]]:
    """Detects if caller requested human escalation."""
    lowered = text.lower()
    for pattern in ESCALATION_TRIGGERS:
        if re.search(pattern, lowered):
            return True, "customer_requested_human"
    return False, None


def detect_objection(text: str) -> Optional[Tuple[str, str]]:
    """
    Detects if the user raised a known objection.
    Returns: (objection_category, objection_reply) or None
    """
    lowered = text.lower()
    for category, config in OBJECTION_RESPONSES.items():
        for pattern in config["patterns"]:
            if re.search(pattern, lowered):
                return category, config["response"]
    return None
