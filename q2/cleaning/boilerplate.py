import re
import html
import unicodedata
from typing import Tuple, List


# Regex patterns for common web/document noise
COOKIE_PATTERNS = [
    r"(?i)\bwe\s+use\s+cookies\b[^\.\n]*?(?:\.|$)",
    r"(?i)\bthis\s+website\s+uses\s+cookies\b[^\.\n]*?(?:\.|$)",
    r"(?i)\baccept\s+all\s+cookies\b\.?",
    r"(?i)\bby\s+clicking\s+['\"]?accept['\"]?,?\s+you\s+agree[^\.\n]*?(?:\.|$)",
    r"(?i)\bcookie\s+settings\s*\|\s*privacy\s+policy\b",
]

NAVIGATION_FOOTER_PATTERNS = [
    r"(?i)^\s*(?:home|about us|contact us|privacy policy|terms of service|blog|faq)\s*(?:\||•|/)\s*(?:home|about us|contact us|privacy policy|terms of service|blog|faq).*?$",
    r"(?i)copyright\s*©?\s*\d{4}.*?(?:all rights reserved|inc\.|llc)\.?",
    r"(?i)follow us on\s*(?:twitter|x|linkedin|facebook|instagram|youtube)\.?",
    r"(?i)subscribe to our newsletter.*?(?:submit|enter email)?\.?",
    r"(?i)powered by\s*[\w\s]+",
]

HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def clean_boilerplate(text: str) -> Tuple[str, List[str]]:
    """
    Cleans raw text by removing HTML tags, cookie notices, header/footer noise,
    control characters, and normalizing unicode.

    Returns:
        (cleaned_text, list_of_removed_noise_labels)
    """
    if not text:
        return "", []

    removed_noise = []

    # 1. Unescape HTML entities (&amp;, &nbsp;, etc.)
    cleaned = html.unescape(text)

    # 2. Strip residual HTML tags
    if "<" in cleaned and ">" in cleaned:
        cleaned = HTML_TAG_PATTERN.sub(" ", cleaned)
        removed_noise.append("html_tags")

    # 3. Unicode normalization (NFKC)
    cleaned = unicodedata.normalize("NFKC", cleaned)

    # 4. Remove zero-width spaces and control characters (preserve \n, \t)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b\u200c\u200d\ufeff]", "", cleaned)

    # 5. Standardize quotes and hyphens
    cleaned = cleaned.replace("“", '"').replace("”", '"')
    cleaned = cleaned.replace("‘", "'").replace("’", "'")
    cleaned = cleaned.replace("—", " - ").replace("–", " - ")

    # 6. Remove cookie notices
    for pattern in COOKIE_PATTERNS:
        matches = re.findall(pattern, cleaned)
        if matches:
            cleaned = re.sub(pattern, "", cleaned)
            removed_noise.append("cookie_notice")

    # 7. Remove navigation / footer boilerplate line-by-line
    lines = cleaned.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped_line = line.strip()
        is_boilerplate = False
        for pattern in NAVIGATION_FOOTER_PATTERNS:
            if re.match(pattern, stripped_line):
                is_boilerplate = True
                removed_noise.append("nav_footer_boilerplate")
                break
        if not is_boilerplate:
            cleaned_lines.append(line.rstrip())

    # 8. Collapse excessive blank lines (more than 2 consecutive newlines -> 2)
    result = "\n".join(cleaned_lines)
    result = re.sub(r"\n{3,}", "\n\n", result).strip()

    return result, list(set(removed_noise))
