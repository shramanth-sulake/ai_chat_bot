# app/filters.py
"""
Basic regex-based content filters and redaction helpers.
Extend this module with company-specific rules as needed.
"""

import re
from typing import Tuple

# Example patterns to detect / redact. Add/remove as needed.
_PATTERNS = {
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    # phone numbers (very permissive)
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\d{6,12})\b"),
}

REDACT_TOKEN = "[REDACTED]"

def redact_text(text: str) -> Tuple[str, bool]:
    """
    Redact any matched sensitive patterns. Returns (redacted_text, had_redaction_bool).
    """
    had = False
    out = text
    for name, pattern in _PATTERNS.items():
        if pattern.search(out):
            had = True
            out = pattern.sub(REDACT_TOKEN, out)
    return out, had

def is_disallowed(text: str) -> bool:
    """
    A quick check whether text contains disallowed content we should not return.
    Extend with more advanced checks as required.
    """
    # Example: if text mentions "password" or "ssn" etc, treat as disallowed
    lowered = text.lower()
    disallowed_keywords = ["password", "ssn", "social security", "credit card cvv"]
    for kw in disallowed_keywords:
        if kw in lowered:
            return True
    return False
