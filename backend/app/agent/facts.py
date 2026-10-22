"""Reject spoken times, prices, discounts, and booking claims the tools did not produce."""

from __future__ import annotations

import re

_ONES = {
    "zero": 0,
    "oh": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)
_RELATIVE = ("tomorrow", "tonight", "today", "next week")
_DISCOUNT = re.compile(
    r"\b(waive|waived|waiver|discount|discounts|free visit|for free|no charge|"
    r"price match|match that|match their|cheapest|%\s*off|percent off)\b",
    re.I,
)
_BOOKED = re.compile(r"\b(booked|confirmed|all set|you're all booked|you are all booked|locked in)\b", re.I)
_CLOCK = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b", re.I)
_MONEY = re.compile(r"\$\s*(\d[\d,]*)(?:\.(\d{2}))?")
_PERCENT = re.compile(r"\b(\d{1,3})\s*(?:%|percent)\b", re.I)
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})[t ](\d{2}):(\d{2})")
_DOWNGRADE = re.compile(
    r"not an emergency|doesn't sound like an emergency|does not sound like an emergency|"
    r"no need to worry|call you back tomorrow",
    re.I,
)


def _fold_numbers(text: str) -> str:
    """Replace number words so 'forty-nine' and 'three in the afternoon' become digits."""

    def word_number(match: re.Match[str]) -> str:
        head = match.group(1).lower()
        tail = (match.group(2) or "").lower()
        if head in _TENS:
            return str(_TENS[head] + (_ONES.get(tail, 0) if tail else 0))
        return str(_ONES[head])

    pattern = re.compile(
        r"\b(zero|oh|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
        r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
        r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)"
        r"(?:[-\s](one|two|three|four|five|six|seven|eight|nine))?\b",
        re.I,
    )
    folded = pattern.sub(word_number, text)
    folded = re.sub(
        r"\b(\d{1,2})(?::(\d{2}))?\s+in the (morning|afternoon|evening)\b",
        lambda match: _clock(int(match.group(1)), int(match.group(2) or 0), match.group(3)),
        folded,
        flags=re.I,
    )
    folded = re.sub(r"\bnoon\b", "12:00 pm", folded, flags=re.I)
    folded = re.sub(r"\bmidnight\b", "12:00 am", folded, flags=re.I)
    return folded


def _clock(hour: int, minute: int, part: str | None) -> str:
    part = (part or "").lower().replace(".", "")
    if part.startswith("p") and hour < 12:
        hour += 12
    if part.startswith("a") and hour == 12:
        hour = 0
    if part == "afternoon" and hour < 12:
        hour += 12
    if part == "evening" and hour < 12:
        hour += 12
    if part == "morning" and hour == 12:
        hour = 0
    suffix = "am" if hour < 12 else "pm"
    hour12 = hour % 12 or 12
    return f"{hour12}:{minute:02d} {suffix}"


def _clocks(text: str) -> set[str]:
    found = set()
    for match in _CLOCK.finditer(text):
        minute = int(match.group(2) or 0)
        found.add(_clock(int(match.group(1)), minute, match.group(3)))
    return found


def _money(text: str) -> set[str]:
    found = set()
    for match in _MONEY.finditer(text):
        dollars = int(match.group(1).replace(",", ""))
        cents = match.group(2) or "00"
        found.add(f"${dollars}.{cents}")
    for match in re.finditer(r"\b(\d{1,5})\s+dollars\b", text, re.I):
        found.add(f"${int(match.group(1))}.00")
    return found


def _percents(text: str) -> set[str]:
    return {f"{int(match.group(1))}%" for match in _PERCENT.finditer(text)}


def _from_iso(text: str) -> set[str]:
    found: set[str] = set()
    for match in _ISO.finditer(text.lower()):
        hour = int(match.group(4))
        minute = int(match.group(5))
        found.add(_clock(hour, minute, "am" if hour < 12 else "pm"))
        month = int(match.group(2))
        day = int(match.group(3))
        found.add(f"{_MONTHS[month - 1]} {day}")
    return found


def facts(text: str) -> set[str]:
    folded = _fold_numbers(text or "")
    lowered = folded.lower()
    found = _clocks(folded) | _money(folded) | _percents(lowered) | _from_iso(lowered)
    for name in _WEEKDAYS:
        if re.search(rf"\b{name}\b", lowered):
            found.add(name)
    for name in _MONTHS:
        match = re.search(rf"\b{name}\s+(\d{{1,2}})\b", lowered)
        if match:
            found.add(f"{name} {int(match.group(1))}")
    for name in _RELATIVE:
        if re.search(rf"\b{name}\b", lowered):
            found.add(name)
    if _DISCOUNT.search(lowered):
        found.add("discount")
    if _BOOKED.search(lowered):
        found.add("booked")
    return found


def speech_supported(spoken: str, allowed: str, *, emergency: bool = False, booked_ok: bool = False) -> bool:
    """Every clock, price, weekday, discount, and booking claim must come from `allowed`."""
    if not spoken:
        return False
    if emergency and _DOWNGRADE.search(spoken):
        return False
    if _DOWNGRADE.search(spoken) and not _DOWNGRADE.search(allowed or ""):
        return False
    spoken_facts = facts(spoken)
    if "booked" in spoken_facts and not booked_ok:
        return False
    allowed_facts = facts(allowed or "")
    if booked_ok:
        allowed_facts.add("booked")
    for token in spoken_facts:
        if token == "booked":
            continue
        if token not in allowed_facts:
            return False
    return True
