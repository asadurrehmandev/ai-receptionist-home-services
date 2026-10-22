"""Reject spoken times and prices that did not come from a tool result."""

from __future__ import annotations

import re

CLOCK = re.compile(r"\b\d{1,2}:\d{2}\s*[ap]m\b", re.I)
MONEY = re.compile(r"\$\d[\d,]*(?:\.\d{2})?")
WEEKDAY = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)
MONTH_DAY = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b",
    re.I,
)
PHONE = re.compile(r"\(\d{3}\)\s*\d{3}-\d{4}")
ZIP = re.compile(r"\b\d{5}\b")
DOWNGRADE = re.compile(
    r"not an emergency|doesn't sound like an emergency|does not sound like an emergency|"
    r"no need to worry|call you back tomorrow|your visit is free|no diagnostic fee|\$0\b|free visit",
    re.I,
)


def entities(text: str) -> set[str]:
    found: set[str] = set()
    for pattern in (CLOCK, MONEY, WEEKDAY, MONTH_DAY, PHONE, ZIP):
        for match in pattern.findall(text or ""):
            found.add(match.lower().replace("  ", " "))
    return found


def speech_supported(spoken: str, allowed: str, *, emergency: bool = False) -> bool:
    """Every time, date, price, phone, and ZIP in `spoken` must appear in `allowed`."""
    if not spoken:
        return False
    if emergency and DOWNGRADE.search(spoken):
        return False
    if DOWNGRADE.search(spoken) and not DOWNGRADE.search(allowed):
        return False
    haystack = (allowed or "").lower()
    for token in entities(spoken):
        if token not in haystack:
            return False
    return True
