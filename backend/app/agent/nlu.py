"""Intent, slot, and emergency detection for the rule-based brain.

The matchers stay deterministic so the scenario suite and the phone path
share one behavior when no LLM key is configured. An LLM, when present,
may rephrase the spoken line. It does not decide bookings or transfers.
"""

from __future__ import annotations

import re

EMERGENCY_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b(burst pipe|pipe burst|burst water pipe|pipe just burst|busted pipe)\b", "Burst pipe"),
    (r"\b(gas smell|smell of gas|smells like gas|smell gas|smelling gas|rotten eggs?)\b", "Gas smell"),
    (r"\b(carbon monoxide|co alarm|co detector)\b", "Carbon monoxide"),
    (r"\b(sewer backup|sewage backup|sewage coming|raw sewage)\b", "Sewer backup"),
    (r"\b(flooding|flooded basement|basement flooded|house is flooded|water everywhere)\b", "Active flooding"),
    (r"\b(sparking|electrical fire|outlet (is )?smoking|burning smell from the panel|smoke from the outlet)\b", "Electrical hazard"),
    (r"no heat.{0,48}(baby|infant|newborn|elderly|freezing)|(baby|infant|elderly|freezing).{0,48}no heat", "No heat with a vulnerable occupant"),
)

SPAM_PATTERNS: tuple[str, ...] = (
    r"\bseo\b",
    r"rank(ing)? on google",
    r"google (business|listing|reviews)",
    r"business listing",
    r"car warranty",
    r"extended warranty",
    r"\bmedicare\b",
    r"solar panels? (sales|offer|deal)",
    r"we (buy|purchase) houses",
    r"marketing services",
    r"lead generation",
    r"press 1 to",
)

SERVICE_PROBLEM = re.compile(
    r"\b(drains?|clogs?|clogged|leaks?|leaking|toilets?|faucets?|disposals?|water heaters?|"
    r"hot water|furnaces?|no heat|not cooling|air condition\w*|a/c|\bac\b|sewers?|repairs?|"
    r"broken|not working|backing up|backed up|jammed|sinks?)\b",
    re.I,
)

EXISTING = re.compile(
    r"\b(reschedul\w*|re-schedule|move my appointment|cancel my (appointment|booking|visit)|"
    r"existing (appointment|booking)|already (booked|scheduled)|my appointment)\b",
    re.I,
)

QUOTE = re.compile(r"\b(how much|how many|price|cost|estimate|quote|ballpark)\b", re.I)

HUMAN = re.compile(
    r"\b(real person|live person|real human|talk to (a )?(human|person|manager|supervisor)|"
    r"speak to (a )?(human|person|manager)|transfer me|actual person)\b",
    re.I,
)

ABANDON = re.compile(
    r"\b(never mind|nevermind|forget it|gotta go|have to go|i(?:'ll| will) call back|"
    r"call back later|not interested|stop calling|hang up)\b",
    re.I,
)

YES = re.compile(
    r"\b(yes|yeah|yep|yup|sure|okay|ok|please do|book it|lock it|confirm|that works|do it|go ahead|sounds good)\b",
    re.I,
)
NO = re.compile(r"\b(no|nope|nah|different time|another time)\b", re.I)

PHONE = re.compile(r"(?:\+?1[\s.\-]?)?(?:\(\d{3}\)|\d{3})[\s.\-]?\d{3}[\s.\-]\d{4}\b")
PHONE_COMPACT = re.compile(r"\b(?:\+?1)?(\d{10})\b")
ZIP = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
STREET = re.compile(
    r"\b(\d{1,6}\s+(?:[A-Za-z0-9.'#-]+\s+){0,6}"
    r"(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Court|Ct|"
    r"Place|Pl|Circle|Cir|Trail|Trl|Parkway|Pkwy))\b",
    re.I,
)

ISSUE_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("water heater", "no hot water", "hot water"), "Water heater"),
    (("clog", "drain", "backing up", "backed up", "slow drain"), "Clogged drain"),
    (("toilet",), "Toilet"),
    (("faucet", "tap"), "Faucet"),
    (("disposal",), "Garbage disposal"),
    (("not cooling", "air condition", "a/c", " ac "), "AC repair"),
    (("furnace", "no heat", "not heating"), "Heating repair"),
    (("sewer", "sewage"), "Sewer line"),
    (("leak",), "Leak"),
)

NAME_STOP = {
    "an",
    "a",
    "the",
    "just",
    "about",
    "calling",
    "trying",
    "having",
    "looking",
    "here",
    "scheduled",
    "calling",
    "from",
    "with",
    "need",
    "have",
    "and",
    "but",
    "my",
    "please",
}


def normalize(text: str) -> str:
    cleaned = text.strip().lower()
    cleaned = cleaned.replace("’", "'")
    cleaned = re.sub(r"[.!?]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _mask_negations(text: str) -> str:
    return re.sub(
        r"\b(?:no|not|without|isn't|isnt|aren't|arent)\b(?:\s+\w+){0,5}\s+"
        r"(gas|burst|flood|sewage|sewer|sparking|carbon)",
        " ",
        text,
        flags=re.I,
    )


def detect_emergency(text: str) -> str | None:
    masked = _mask_negations(normalize(text))
    for pattern, label in EMERGENCY_PATTERNS:
        if re.search(pattern, masked, re.I):
            return label
    return None


def is_spam(text: str) -> bool:
    norm = normalize(text)
    strong = re.search(r"seo|warranty|medicare|marketing services|lead generation|press 1 to", norm)
    if SERVICE_PROBLEM.search(norm) and not strong:
        return False
    return any(re.search(pattern, norm) for pattern in SPAM_PATTERNS)


def detect_intent(text: str) -> str:
    if detect_emergency(text):
        return "emergency"
    if is_spam(text):
        return "spam"
    norm = normalize(text)
    if EXISTING.search(norm):
        return "existing_booking"
    if QUOTE.search(norm):
        return "quote"
    if SERVICE_PROBLEM.search(norm) or re.search(
        r"\b(need someone|come out|schedule|book a|repair|broken|problem|technician)\b", norm
    ):
        return "new_job"
    return "unclear"


def wants_human(text: str) -> bool:
    return bool(HUMAN.search(normalize(text)))


def wants_abandon(text: str) -> bool:
    return bool(ABANDON.search(normalize(text)))


def is_yes(text: str) -> bool:
    norm = normalize(text)
    if is_no(norm) and not re.search(r"\b(yes|yeah|yep|sure|book it)\b", norm):
        return False
    return bool(YES.search(norm))


def is_no(text: str) -> bool:
    return bool(NO.search(normalize(text)))


def wants_cancel(text: str) -> bool:
    return bool(re.search(r"\bcancel\b", normalize(text)))


def wants_reschedule(text: str) -> bool:
    return bool(re.search(r"\b(reschedul\w*|re-schedule|move (my |the )?appointment|different (day|time))\b", normalize(text)))


def _digits(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def extract_phone(text: str) -> tuple[str | None, str]:
    """Return (10-digit phone, text with the phone removed)."""
    match = PHONE.search(text)
    if match:
        digits = _digits(match.group(0))
        if len(digits) == 10:
            blanked = text[: match.start()] + " " + text[match.end() :]
            return digits, blanked
    match = PHONE_COMPACT.search(text)
    if match:
        digits = _digits(match.group(1))
        if len(digits) == 10:
            blanked = text[: match.start()] + " " + text[match.end() :]
            return digits, blanked
    return None, text


def extract_zip(text: str) -> str | None:
    _, stripped = extract_phone(text)
    match = ZIP.search(stripped)
    return match.group(1) if match else None


def extract_street(text: str) -> str | None:
    match = STREET.search(text)
    if not match:
        return None
    street = re.sub(r"\s+", " ", match.group(1)).strip(" ,.")
    parts = street.split()
    if not parts:
        return None
    parts[0] = parts[0]
    titled = [parts[0]]
    for word in parts[1:]:
        titled.append(word.upper() if len(word) <= 2 and word.isalpha() else word.capitalize())
    # Keep common street suffixes tidy (St, Ave already capitalized).
    return " ".join(titled)


def extract_city(text: str, cities: tuple[str, ...]) -> str | None:
    norm = normalize(text)
    for city in sorted(cities, key=len, reverse=True):
        if re.search(rf"\b{re.escape(city.lower())}\b", norm):
            return city
    return None


def extract_issue(text: str) -> str | None:
    padded = f" {normalize(text)} "
    for keywords, label in ISSUE_RULES:
        for keyword in keywords:
            token = keyword if keyword.startswith(" ") else keyword
            if token in padded or keyword in padded:
                return label
    return None


def extract_introduced_name(text: str) -> str | None:
    match = re.search(
        r"\b(?:my name is|this is|i am|i'm|im)\s+([a-z][\w']*(?:\s+[a-z][\w']*){0,3})",
        normalize(text),
        re.I,
    )
    if not match:
        return None
    chunk = match.group(1)
    chunk = re.split(
        r"\b(?:and|but|at|from|in|on|my|calling|need|have|with|the|phone|i|please|cancel|reschedule|appointment|about)\b",
        chunk,
        maxsplit=1,
    )[0]
    tokens = [re.sub(r"[^a-z']", "", token) for token in chunk.split()]
    tokens = [token for token in tokens if token and token not in NAME_STOP and token.isalpha()]
    tokens = tokens[:3]
    if not tokens:
        return None
    if tokens[0] in NAME_STOP:
        return None
    return " ".join(token.capitalize() for token in tokens[:3])


def guess_bare_name(text: str) -> str | None:
    introduced = extract_introduced_name(text)
    if introduced:
        return introduced
    cleaned = re.sub(r"[^A-Za-z\s'-]", " ", text).strip()
    parts = [part for part in cleaned.split() if part]
    if not 1 <= len(parts) <= 3:
        return None
    if parts[0].lower() in NAME_STOP or parts[0].lower() in {"yes", "no", "yeah", "ok", "okay"}:
        return None
    return " ".join(part.capitalize() for part in parts)


def format_phone(digits: str | None) -> str:
    if not digits:
        return ""
    raw = re.sub(r"\D", "", digits)
    if len(raw) == 11 and raw.startswith("1"):
        raw = raw[1:]
    if len(raw) != 10:
        return digits
    return f"({raw[:3]}) {raw[3:6]}-{raw[6:]}"


def selection_index(text: str) -> int | None:
    norm = normalize(text)
    if re.search(r"\b(earliest|soonest|first one|first available|the first|asap|as soon as possible)\b", norm):
        return 0
    if re.search(r"\b(second|2nd|the other one|middle one)\b", norm):
        return 1
    if re.search(r"\b(third|3rd|the last one|last option)\b", norm):
        return 2
    return None
