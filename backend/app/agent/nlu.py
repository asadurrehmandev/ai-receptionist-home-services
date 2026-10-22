"""Intent, slot, and emergency detection.

Matchers stay deterministic so the phone path and the no-key fallback share
one behavior. When Claude is configured it may choose tools, but it does not
invent times, prices, or transfers. A definite emergency is forced here,
before any model call.
"""

from __future__ import annotations

import re

from app.agent.hazard import classify_emergency as classify_hazard

SPAM_PATTERNS: tuple[str, ...] = (
    r"\bseo\b",
    r"\bads\b",
    r"\badvertising\b",
    r"rank(ing)? on google",
    r"google (business|listing|reviews)",
    r"business listing",
    r"\byelp\b",
    r"lower your rates",
    r"car warranty",
    r"extended warranty",
    r"\bmedicare\b",
    r"solar panels? (sales|offer|deal)",
    r"we (buy|purchase) houses",
    r"marketing services",
    r"lead generation",
    r"press 1 to",
    r"auto loan",
)

SERVICE_PROBLEM = re.compile(
    r"\b(drains?|clogs?|clogged|unclog|leaks?|leaking|toilets?|faucets?|disposals?|water heaters?|"
    r"hot water|furnaces?|no heat|not cooling|air condition\w*|a/c|\bac\b|sewers?|repairs?|"
    r"broken|not working|backing up|backed up|jammed|sinks?|heeder|heder)\b",
    re.I,
)

EXISTING = re.compile(
    r"\b(reschedul\w*|re-schedule|move my appointment|cancel my (appointment|booking|visit)|"
    r"existing (appointment|booking)|already (booked|scheduled)|my appointment|need to cancel|"
    r"want to cancel|cancel the appointment)\b",
    re.I,
)

QUOTE = re.compile(
    r"\b(how much|how many|price|cost|estimate|quot\w*|ballpark|beat that|beat this|can you beat|"
    r"cheapest|discount|waive|price match|cash price|bucks)\b",
    re.I,
)

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
CLEAN_YES_BLOCK = re.compile(r"\b(wait|which|hold on|actually|but|maybe|or)\b|\?", re.I)
NO = re.compile(r"\b(no|nope|nah|different time|another time)\b", re.I)

PHONE = re.compile(r"(?:\+?1[\s.\-]?)?(?:\(\d{3}\)|\d{3})[\s.\-]?\d{3}[\s.\-]\d{4}\b")
PHONE_COMPACT = re.compile(r"\b(?:\+?1)?(\d{10})\b")
ZIP = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
STREET_SUFFIX = (
    r"Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Court|Ct|"
    r"Place|Pl|Circle|Cir|Trail|Trl|Parkway|Pkwy|Plaza|Loop|Pass|Cove|Path|Highway|Hwy|FM|RR"
)
STREET = re.compile(
    rf"\b(\d{{1,6}}\s+(?:[A-Za-z0-9.'#-]+\s+){{0,6}}(?:{STREET_SUFFIX}))\b",
    re.I,
)

ISSUE_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("water heater", "water heeder", "water heder", "no hot water", "hot water"), "Water heater"),
    (("clog", "drain", "backing up", "backed up", "slow drain"), "Clogged drain"),
    (("toilet",), "Toilet"),
    (("faucet", "tap"), "Faucet"),
    (("disposal",), "Garbage disposal"),
    (("not cooling", "air condition", "a/c", " ac ", "blowing warm"), "AC repair"),
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
    "from",
    "with",
    "need",
    "have",
    "and",
    "but",
    "my",
    "please",
    "so",
    "worried",
    "sorry",
    "hold",
    "okay",
    "ok",
    "dog",
    "hi",
    "hey",
    "um",
    "uh",
    "well",
    "yes",
    "no",
    "yeah",
    "yep",
    "earliest",
    "calling",
    "really",
    "very",
    "its",
    "it's",
}

DIGIT_WORDS = {
    "zero": "0",
    "oh": "0",
    "o": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}

SPANISH_HINTS = (
    "hola",
    "gracias",
    "por favor",
    "tengo",
    "fuga",
    "agua",
    "fregadero",
    "huele",
    "olor",
    "cocina",
    "ayuda",
    "estufa",
    "cita",
    "calefaccion",
    "baño",
    "bano",
    "inundando",
    "inundada",
    "chispas",
    "alcantarilla",
    "casa",
    "fuerte",
    "hay",
)


def normalize(text: str) -> str:
    cleaned = text.strip().lower()
    cleaned = cleaned.replace("’", "'").replace("—", " ").replace("–", " ")
    cleaned = re.sub(r"[.!?]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def classify_emergency(text: str) -> tuple[str, str | None]:
    """Return ('definite'|'advice'|'none', label). Concepts live in hazard.py."""
    return classify_hazard(text)


def detect_emergency(text: str) -> str | None:
    level, label = classify_emergency(text)
    if level == "definite":
        return label
    return None


def is_spam(text: str) -> bool:
    norm = normalize(text)
    strong = re.search(
        r"seo|warranty|medicare|marketing services|lead generation|press 1 to|auto loan|business listing",
        norm,
    )
    if SERVICE_PROBLEM.search(norm) and not strong:
        return False
    return any(re.search(pattern, norm) for pattern in SPAM_PATTERNS)


def looks_spanish(text: str) -> bool:
    norm = normalize(text)
    hits = [hint for hint in SPANISH_HINTS if re.search(rf"\b{re.escape(hint)}\b", norm)]
    return len(hits) >= 2 or "hola" in hits or "huele" in hits


def is_haggle(text: str) -> bool:
    return bool(
        re.search(
            r"\b(beat|match that|match their|cheaper|cheapest|for fifty|bucks|discount|"
            r"can you do it for|waive|cash|fixed income|price match)\b",
            normalize(text),
        )
    )


def detect_intent(text: str) -> str:
    if detect_emergency(text):
        return "emergency"
    if is_spam(text):
        return "spam"
    norm = normalize(text)
    if EXISTING.search(norm):
        return "existing_booking"
    if QUOTE.search(norm) or is_haggle(norm):
        return "quote"
    if SERVICE_PROBLEM.search(norm) or re.search(
        r"\b(need someone|come out|schedule|book a|repair|broken|problem|technician|inspect\w*|checked|check my|check it)\b",
        norm,
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


def is_clean_yes(text: str) -> bool:
    """A cancel confirmation. Questions, hedges, and a new time do not count."""
    raw = text or ""
    if CLEAN_YES_BLOCK.search(raw):
        return False
    if re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|noon|\d{1,2}\s*(?:am|pm))\b", raw, re.I):
        return False
    return is_yes(raw)


def is_no(text: str) -> bool:
    return bool(NO.search(normalize(text)))


def wants_cancel(text: str) -> bool:
    return bool(re.search(r"\bcancel\b", normalize(text)))


def wants_reschedule(text: str) -> bool:
    return bool(re.search(r"\b(reschedul\w*|re-schedule|move (my |the )?appointment|different (day|time))\b", normalize(text)))


def is_correction(text: str) -> bool:
    return bool(re.search(r"\b(no wait|sorry|actually|i meant|correction)\b", normalize(text)))


def _digits(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def expand_spoken_numbers(text: str) -> str:
    """Turn 'five one two' and 'double five' into digits. Leaves other words alone."""

    def convert(match: re.Match[str]) -> str:
        words = match.group(0).split()
        out: list[str] = []
        index = 0
        while index < len(words):
            word = words[index].lower()
            if word == "double" and index + 1 < len(words) and words[index + 1].lower() in DIGIT_WORDS:
                out.append(DIGIT_WORDS[words[index + 1].lower()] * 2)
                index += 2
                continue
            if word not in DIGIT_WORDS:
                return match.group(0)
            out.append(DIGIT_WORDS[word])
            index += 1
        return "".join(out)

    pattern = re.compile(
        r"\b(?:double|zero|oh|o|one|two|three|four|five|six|seven|eight|nine)"
        r"(?:\s+(?:double|zero|oh|o|one|two|three|four|five|six|seven|eight|nine)){1,}\b",
        re.I,
    )
    return pattern.sub(convert, text)


def extract_phone(text: str) -> tuple[str | None, str]:
    """Return (10-digit phone, text with the phone removed)."""
    source = expand_spoken_numbers(text)
    if is_correction(text):
        tail = re.split(r"no wait|sorry|actually|i meant", source, maxsplit=1, flags=re.I)[-1]
        found, blanked = _phone_in(tail)
        if found:
            return found, blanked
    return _phone_in(source)


def _phone_in(text: str) -> tuple[str | None, str]:
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
    source = expand_spoken_numbers(stripped)
    matches = list(ZIP.finditer(source))
    if not matches:
        return None
    usable: list[str] = []
    for match in matches:
        before = source[: match.start()].strip(" ,.")
        token = match.group(1)
        entire = source.strip(" ,.") == token
        if not before and not entire:
            continue
        usable.append(token)
    if not usable:
        return None
    return usable[-1]


def _tidy_street(street: str) -> str:
    street = re.sub(r"\s+", " ", street).strip(" ,.")
    parts = street.split()
    if not parts:
        return street
    titled = [parts[0]]
    for word in parts[1:]:
        titled.append(word.upper() if len(word) <= 2 and word.isalpha() else word.capitalize())
    return " ".join(titled)


UNIT = re.compile(r"\b(apartment|apt|unit|suite|#)\s*([A-Za-z0-9-]+)\b", re.I)
_UNIT_LABEL = {"apartment": "Apartment", "apt": "Apt", "unit": "Unit", "suite": "Suite", "#": "#"}


def extract_unit(text: str) -> str | None:
    match = UNIT.search(text)
    if not match:
        return None
    label = _UNIT_LABEL[match.group(1).lower()]
    return f"{label} {match.group(2).upper()}"


def last4_correction(text: str) -> str | None:
    """A spoken fix for the last four digits, such as '0178 at the end'."""
    match = re.search(
        r"\b(\d{4})\b\s+at the end\b|\bat the end\b(?:\s+(?:is|should be))?\s*(\d{4})\b",
        text or "",
        re.I,
    )
    if not match:
        return None
    return match.group(1) or match.group(2)


def house_correction(text: str) -> tuple[str, str] | None:
    """Return (new house number, old house number) for '1907 not 1905'."""
    match = re.search(r"\b(\d{1,6})\s+not\s+(\d{1,6})\b", text or "", re.I)
    if not match:
        return None
    return match.group(1), match.group(2)


def extract_street(text: str, cities: tuple[str, ...] = ()) -> str | None:
    source = text
    if is_correction(text):
        source = re.split(r"\b(?:actually|i meant|correction)\b", text, maxsplit=1, flags=re.I)[-1]
    match = STREET.search(source)
    if match and not re.search(r"\bat the end\b", match.group(1), re.I):
        return _with_unit(_tidy_street(match.group(1)), source)
    city_pattern = "|".join(re.escape(city) for city in cities) if cities else r"$^"
    loose = re.search(
        rf"\b(\d{{1,6}}\s+[A-Za-z][A-Za-z.'-]{{1,}}(?:\s+[A-Za-z][A-Za-z.'-]{{1,}}){{0,3}})"
        rf"(?=\s*(?:,|\b(?:{city_pattern})\b|\b\d{{5}}\b|\b(?:apartment|apt|unit|suite)\b|$))",
        source,
        re.I,
    )
    if not loose:
        return None
    candidate = loose.group(1).strip(" ,.")
    if re.search(r"\b(yes|yeah|earliest|tomorrow|phone|number)\b", candidate, re.I):
        return None
    if re.search(r"\bat the end\b", candidate, re.I):
        return None
    return _with_unit(_tidy_street(candidate), source)


def _with_unit(street: str, source: str) -> str:
    unit = extract_unit(source)
    if unit and unit.lower() not in street.lower():
        return f"{street} {unit}"
    return street


def extract_city(text: str, cities: tuple[str, ...]) -> str | None:
    norm = normalize(text)
    for city in sorted(cities, key=len, reverse=True):
        if re.search(rf"\b{re.escape(city.lower())}\b", norm):
            return city
    return None


def extract_issue(text: str) -> str | None:
    padded = f" {normalize(text).replace('heeder', 'heater').replace('heder', 'heater')} "
    for keywords, label in ISSUE_RULES:
        for keyword in keywords:
            if keyword in padded:
                return label
    return None


def spelled_word(text: str) -> str | None:
    match = re.search(r"\b([A-Za-z](?:-[A-Za-z]){2,})\b", text)
    if not match:
        return None
    letters = match.group(1).split("-")
    if all(len(letter) == 1 for letter in letters):
        return "".join(letters).capitalize()
    return None


def _proper_token(token: str) -> str:
    if "-" in token:
        return "-".join(_proper_token(part) for part in token.split("-"))
    if "'" in token:
        return "'".join(part[:1].upper() + part[1:] if part else "" for part in token.split("'"))
    return token[:1].upper() + token[1:]


def _name_chars(token: str) -> str:
    return "".join(char for char in token if char.isalpha() or char in "-'")


def _plausible_name(value: str) -> bool:
    parts = value.split()
    if not 1 <= len(parts) <= 3:
        return False
    for part in parts:
        if part.lower() in NAME_STOP:
            return False
        if not part or not any(char.isalpha() for char in part):
            return False
        if not all(char.isalpha() or char in "-'" for char in part):
            return False
    if parts[0].lower() in NAME_STOP:
        return False
    return True


def extract_introduced_name(text: str) -> str | None:
    match = re.search(
        r"\b(?:my name is|this is|i am|i'm|im)\s+([^\W\d_](?:[^\W\d_]|['-])*(?:\s+[^\W\d_](?:[^\W\d_]|['-])*){0,3})",
        text,
        re.I,
    )
    if not match:
        return None
    chunk = match.group(1)
    chunk = re.split(
        r"\b(?:and|but|at|from|in|on|my|calling|need|have|with|the|phone|i|please|cancel|reschedule|appointment|about|number)\b",
        chunk,
        maxsplit=1,
        flags=re.I,
    )[0]
    tokens = [_name_chars(token) for token in chunk.split()]
    tokens = [token for token in tokens if token and token.lower() not in NAME_STOP]
    if not tokens or tokens[0].lower() in NAME_STOP:
        return None
    if len(tokens) == 1:
        return None
    candidate = " ".join(_proper_token(token) for token in tokens[:3])
    if not _plausible_name(candidate):
        return None
    return candidate


def guess_bare_name(text: str) -> str | None:
    introduced = extract_introduced_name(text)
    if introduced:
        return introduced
    trailing = re.findall(r"\b([A-Z][a-z]+(?:['-][A-Z][a-z]+)?)\s+([A-Z][a-z]+(?:['-][A-Z][a-z]+)?)\b", text)
    if trailing:
        first, last = trailing[-1]
        candidate = f"{first} {last}"
        if _plausible_name(candidate):
            return candidate
    cleaned = "".join(char if (char.isalpha() or char in " '-") else " " for char in text).strip()
    parts = [part for part in cleaned.split() if part]
    if not 2 <= len(parts) <= 3:
        return None
    if any(part.lower() in NAME_STOP for part in parts):
        return None
    candidate = " ".join(_proper_token(part) for part in parts)
    if not _plausible_name(candidate):
        return None
    return candidate


def format_phone(digits: str | None) -> str:
    if not digits:
        return ""
    raw = re.sub(r"\D", "", digits)
    if len(raw) == 11 and raw.startswith("1"):
        raw = raw[1:]
    if len(raw) != 10:
        return digits
    return f"({raw[:3]}) {raw[3:6]}-{raw[6:]}"


def caller_id_digits(value: str | None) -> str | None:
    if not value:
        return None
    digits = _digits(value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits if len(digits) == 10 else None


def selection_index(text: str) -> int | None:
    norm = normalize(text)
    if re.search(r"\b(earliest|soonest|first one|first available|the first|asap|as soon as possible)\b", norm):
        return 0
    if re.search(r"\b(second|2nd|the other one|middle one)\b", norm):
        return 1
    if re.search(r"\b(third|3rd|the last one|last option)\b", norm):
        return 2
    return None
