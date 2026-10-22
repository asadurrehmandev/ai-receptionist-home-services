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
    r"cheapest|discount|waive|price match|cash price|bucks|after[- ]hours|\brate\b)\b",
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
    r"\b(yes|yeah|yep|yup|sure|okay|ok|please do|book it|lock it|confirm|that works|do it|go ahead|sounds good|"
    r"sí|si|claro|confirmo|de acuerdo)\b",
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
# A single letter or digit after the suffix stays in the street ("Avenue B").
# One character plus a word boundary, so "Street Suite" does not swallow Suite.
STREET = re.compile(
    rf"\b(\d{{1,6}}\s+(?:[A-Za-z0-9.'#-]+\s+){{0,6}}(?:{STREET_SUFFIX})(?:\s+[A-Za-z0-9])?)\b",
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
    (("spigot", "hose bib", "hose bibb", "sillcock", "outdoor faucet"), "Outdoor faucet"),
    (("water pressure", "low pressure", "shower pressure"), "Water pressure"),
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
    "necesito",
    "quiero",
    "tengo",
    "reparar",
    "arreglar",
    "calentador",
    "urgente",
    "cotizacion",
    "presupuesto",
    "mantenimiento",
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
    "bano",
    "inundando",
    "inundada",
    "inundacion",
    "chispas",
    "alcantarilla",
    "casa",
    "fuerte",
    "mareado",
    "mareada",
    "mareo",
    "sonando",
    "monoxido",
    "sotano",
    "tuberia",
    "desague",
    "llave",
    "grifo",
    "tecnico",
    "visita",
    "apellido",
    "direccion",
    "telefono",
)


def _fold_latin(text: str) -> str:
    import unicodedata

    pieces: list[str] = []
    for char in text or "":
        decomposed = unicodedata.normalize("NFKD", char)
        pieces.append("".join(item for item in decomposed if not unicodedata.combining(item)))
    return "".join(pieces).lower()


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
    norm = _fold_latin(normalize(text))
    hits = [hint for hint in SPANISH_HINTS if re.search(rf"\b{re.escape(hint)}\b", norm)]
    if "hola" in hits or "huele" in hits:
        return True
    if re.search(r"[¿¡ñ]", text or ""):
        return len(hits) >= 1
    return len(hits) >= 2


_OTHER_SCRIPT = re.compile(
    r"[\u0400-\u04FF\u0900-\u097F\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF\u0600-\u06FF]"
)
_OTHER_WORDS = (
    "odeur",
    "gaz",
    "rieche",
    "wasser",
    "keller",
    "cheiro",
    "inond",
    "mùi",
    "ngập",
    "zapach",
    "pachnie",
    "überschwemmt",
    "steckdose",
    "odeur",
)


_ES_QUOTE = re.compile(
    r"\b(cotizacion|presupuesto|cuanto cuesta|cuanto sale|cuanto cobran)\b",
    re.I,
)
_ES_EXISTING = re.compile(
    r"\b(reprogram\w*|cancelar (?:mi |la )?(?:cita|visita)|cambiar (?:mi |la )?cita|mover (?:mi |la )?cita)\b",
    re.I,
)
_ES_JOB = re.compile(
    r"\b(repar\w*|arregl\w*|calentador|fuga|gote\w*|desague|drenaje|tuberia|"
    r"mantenimiento|sin agua caliente|no calienta|no enfria|inodoro|llave|grifo|"
    r"aire acondicionado|climatizacion|calefaccion|fuga de agua)\b",
    re.I,
)


def _spanish_intent(text: str) -> str | None:
    folded = _fold_latin(normalize(text))
    if not looks_spanish(text):
        return None
    if _ES_EXISTING.search(folded):
        return "existing_booking"
    if _ES_QUOTE.search(folded):
        return "quote"
    if _ES_JOB.search(folded):
        return "new_job"
    return None


def detect_language(text: str) -> str:
    """Return en, es, or other. Spanish books. Other languages get a callback."""
    if looks_spanish(text):
        return "es"
    if _OTHER_SCRIPT.search(text or ""):
        return "other"
    norm = normalize(text)
    if any(re.search(rf"\b{re.escape(word)}\b", norm) for word in _OTHER_WORDS if word.isascii()):
        return "other"
    if any(word in (text or "").lower() for word in _OTHER_WORDS if not word.isascii()):
        return "other"
    return "en"


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
    spanish = _spanish_intent(text)
    if spanish:
        return spanish
    if SERVICE_PROBLEM.search(norm) or re.search(
        r"\b(need someone|come out|schedule|book a|repair|broken|problem|technician|inspect\w*|checked|check my|check it|"
        r"install\w*|hook\s?up|hookup|thermostat|no power|dead outlet|outlet (?:is )?dead|puddle|dripp\w*|"
        r"chilly|cold room|breaker tripped|tripped (?:the )?breaker|blank screen|tune[- ]?up|"
        r"spigots?|hose bibs?|bibbs?|sillcocks?|water pressure|low pressure|shower pressure|"
        r"sump|exhaust fan|gfci|gfi|flood sensors?|softener|check-?up|checkup|replac\w*|"
        r"heat[- ]?pump|annual service|yearly service|yearly check|annual check|maintenance visit|"
        r"landlord|rental unit|inspection)\b",
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
    """A confirmation. Questions, hedges, and a new time do not count."""
    raw = text or ""
    if CLEAN_YES_BLOCK.search(raw):
        return False
    if re.search(r"\b(let me check|check with|not sure|i'll think|ill think|maybe later)\b", raw, re.I):
        return False
    if re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|noon|\d{1,2}\s*(?:am|pm))\b", raw, re.I):
        return False
    return is_yes(raw)


def is_no(text: str) -> bool:
    return bool(NO.search(normalize(text)))


_DANGER_WORD = re.compile(
    r"\b(danger|hurt|injured|injury|emergency|unsafe|sick|bleeding|unconscious)\b",
    re.I,
)
_NEGATION_NEAR = re.compile(
    r"\b(no|not|nobody|no one|none|isn't|isnt|is not|aren't|arent|nothing|nobody's|nobodys)\b",
    re.I,
)


def is_negated_danger(text: str) -> bool:
    """True when the caller is saying the danger word does not apply."""
    raw = text or ""
    if re.search(
        r"\b(?:we(?:'re| are)|everyone(?:'s| is)|everybody(?:'s| is))\s+(?:fine|ok|okay|safe)\b",
        raw,
        re.I,
    ):
        return True
    for match in _DANGER_WORD.finditer(raw):
        window = raw[max(0, match.start() - 48) : match.start()]
        tokens = re.findall(r"[A-Za-z']+", window)
        tail = " ".join(tokens[-4:]).lower()
        if _NEGATION_NEAR.search(tail):
            return True
    return False


def danger_affirmed(text: str) -> bool:
    """A yes, or an unnegated danger word. 'Yes, call me back' still affirms."""
    if is_negated_danger(text):
        return False
    if is_yes(text):
        return True
    for match in _DANGER_WORD.finditer(text or ""):
        window = (text or "")[max(0, match.start() - 48) : match.start()]
        tokens = re.findall(r"[A-Za-z']+", window)
        tail = " ".join(tokens[-4:]).lower()
        if not _NEGATION_NEAR.search(tail):
            return True
    return False


def wants_callback(text: str) -> bool:
    return bool(
        re.search(
            r"\b(person|callback|call me|call back|human|someone call|ring me)\b",
            text or "",
            re.I,
        )
    )


def is_garbled(text: str) -> bool:
    words = re.findall(r"[A-Za-z]{2,}", text or "")
    if not words:
        return True
    return len(words) == 1 and len(words[0]) <= 2


_CLAUSE_SPLIT = re.compile(r"\b(?:but|except|actually|however|though|although)\b|[,;]|—|–", re.I)
_HARM = re.compile(
    r"\b("
    r"dizz\w*|lightheaded|faint(?:ed|ing)?|passed out|collapsed|"
    r"can(?:not|'t) breathe|trouble breathing|wheez\w*|asthma|"
    r"throwing up|vomit\w*|nause\w*|confused|hard to wake|won'?t wake|unresponsive|"
    r"headaches?|chest pain|burns?|burned|burning|"
    r"hurt|injured|injur\w*|bleeding|unconscious|sick|"
    r"fell|fallen|can(?:not|'t) get up|"
    r"smoke|smoking|fire|flames?|sparks?|"
    r"getting worse|spreading|coming faster|"
    r"danger|emergency|unsafe"
    r")\b",
    re.I,
)
_HEDGE_OR_URGENCY = re.compile(
    r"\b("
    r"i think so|maybe|possibly|probably|kind of|sort of|uh huh|mm-?hmm|i guess|"
    r"not sure|unsure|don'?t know|do not know|hurry|quick|help|wait"
    r")\b",
    re.I,
)
_CLEAR_PHRASE = re.compile(
    r"\b(?:"
    r"nobody(?:'s| is) (?:in danger|hurt|injured)|"
    r"no one is (?:hurt|injured|in danger|unsafe)|"
    r"nothing is unsafe|"
    r"(?:this |that |it )?is not an emergency|not an emergency|no emergency|"
    r"we(?:'re| are) (?:fine|ok|okay|safe)|"
    r"we aren'?t in danger|we are not in danger|"
    r"everyone(?:'s| is) (?:fine|ok|okay|safe)|"
    r"everybody(?:'s| is) (?:fine|ok|okay|safe)"
    r")\b",
    re.I,
)
_CLEAR_FILLER = re.compile(
    r"\b(i|we|this|that|it|is|are|a|an|the|please|thanks|thank|you|and|just|really|"
    r"right|now|no|nope|nah|not|nobody|nothing|none|one|in|an)\b",
    re.I,
)
_BARE_NO = re.compile(r"^(?:no|nope|nah|no thanks|no thank you)$", re.I)
_NEGATION_TOKEN = {
    "no",
    "not",
    "nobody",
    "nobodys",
    "nothing",
    "none",
    "isnt",
    "arent",
    "without",
    "dont",
    "never",
    "nope",
    "nah",
    "noone",
}


def _harm_in_clause(clause: str) -> bool:
    for match in _HARM.finditer(clause):
        window = clause[max(0, match.start() - 48) : match.start()]
        tokens = [token.replace("'", "") for token in re.findall(r"[a-z']+", window.lower())]
        tail = tokens[-5:]
        if "no" in tail and "one" in tail:
            continue
        if any(token in _NEGATION_TOKEN for token in tail):
            continue
        return True
    return False


def reports_harm(text: str) -> bool:
    """True when any clause, including one after a leading no, states harm."""
    for clause in _CLAUSE_SPLIT.split(text or ""):
        if clause.strip() and _harm_in_clause(clause):
            return True
    return False


def _explicit_clear(text: str) -> bool:
    raw = " ".join((text or "").replace("'", "'").split())
    folded = re.sub(r"[^a-z']+", " ", raw.lower()).strip()
    if _BARE_NO.fullmatch(folded):
        return True
    if not _CLEAR_PHRASE.search(raw):
        return False
    leftover = _CLEAR_PHRASE.sub(" ", raw)
    leftover = _CLEAR_FILLER.sub(" ", leftover)
    return not re.findall(r"[a-z]{3,}", leftover.lower())


_NATURAL_NO = re.compile(
    r"\b(?:nope|nah|no)\b|"
    r"\bnot at all\b|"
    r"\bnothing like that\b|"
    r"\bnot that i know of\b|"
    r"\bnot that i can tell\b|"
    r"\ball clear\b|"
    r"\bwe(?:'re| are) (?:fine|ok|okay|safe|good)\b|"
    r"\ball good\b|"
    r"\beveryone(?:'s| is) (?:fine|ok|okay|safe|good)\b|"
    r"\beverybody(?:'s| is) (?:fine|ok|okay|safe|good)\b|"
    r"\bnobody(?:'s| is)?(?:\s+\w+){0,4}\s+(?:hurt|injured|in danger)|"
    r"\bno one is (?:in )?(?:any )?(?:danger|hurt|injured)|"
    r"\bnot an emergency\b|"
    r"\bthe house is fine\b",
    re.I,
)
_CAN_WAIT = re.compile(r"\b(?:it|this|that|and it|and this)?\s*(?:can|could)\s+wait\b", re.I)


def _hedge_or_urgency(text: str) -> bool:
    """'It can wait' is not urgency. A bare 'wait' or 'hurry' still is."""
    scrubbed = _CAN_WAIT.sub(" ", text or "")
    return bool(_HEDGE_OR_URGENCY.search(scrubbed))


def _natural_no(text: str) -> bool:
    return bool(_NATURAL_NO.search(text or ""))


_SAFETY_YES = re.compile(r"\b(yes|yeah|yep|yup)\b", re.I)
_FLED = re.compile(
    r"\b(got out|gotten out|left the (?:house|building|home)|evacuat\w*|"
    r"went outside|stepped outside|(?:are|we're|we are) outside|standing outside|"
    r"exited the house|moved out to)\b",
    re.I,
)


def safety_decision(text: str) -> str:
    """How to treat an answer to the safety question.

    A yes pages even if the caller adds that they have gone outside. A natural
    no clears unless the rest of the turn still describes a definite hazard.
    An unclear answer pages.
    """
    raw = text or ""
    if reports_harm(raw):
        return "page"
    if _SAFETY_YES.search(raw) or (_FLED.search(raw) and not _natural_no(raw)):
        return "page"
    if _hedge_or_urgency(raw):
        return "page"
    if _natural_no(raw):
        remainder = _NATURAL_NO.sub(" ", raw)
        remainder = _CAN_WAIT.sub(" ", remainder)
        level, _why = classify_emergency(remainder)
        if level == "definite":
            return "page"
        return "clear"
    if _explicit_clear(raw):
        return "clear"
    if is_yes(raw):
        return "page"
    if wants_callback(raw):
        return "callback"
    return "page"


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
    """Turn 'five one two', 'five-one-two', and 'double five' into digits."""
    text = re.sub(
        r"\b((?:zero|oh|o|one|two|three|four|five|six|seven|eight|nine)(?:-(?:zero|oh|o|one|two|three|four|five|six|seven|eight|nine))+)\b",
        lambda match: match.group(1).replace("-", " "),
        text or "",
        flags=re.I,
    )

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
    """A spoken fix for the last four digits, such as 'ends in 0178' or '0178 at the end'."""
    match = re.search(
        r"\bends in\s+(\d{4})\b|"
        r"\b(\d{4})\b\s+at the end\b|"
        r"\bat the end\b(?:\s+(?:is|should be))?\s*(\d{4})\b",
        text or "",
        re.I,
    )
    if not match:
        return None
    return next(group for group in match.groups() if group)


def house_correction(text: str) -> tuple[str, str] | None:
    """Return (new house number, old house number) for '1907 not 1905'."""
    match = re.search(r"\b(\d{1,6})\s+not\s+(\d{1,6})\b", text or "", re.I)
    if not match:
        return None
    return match.group(1), match.group(2)


_NOT_A_STREET = re.compile(r"\b(?:inside|outside|with|degrees?|years?|year-old)\b", re.I)


def extract_street(text: str, cities: tuple[str, ...] = (), answering: bool = False) -> str | None:
    """A street needs a suffix, unless this turn is the address answer.

    A temperature or an age is never a street, even on the address question.
    """
    source = text or ""
    if is_correction(source):
        source = re.split(r"\b(?:actually|i meant|correction)\b", source, maxsplit=1, flags=re.I)[-1]
    match = STREET.search(source)
    if match and not re.search(r"\bat the end\b", match.group(1), re.I):
        body = match.group(1)
        if not _NOT_A_STREET.search(body):
            return _with_unit(_tidy_street(body), source)
    if not answering:
        return None
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
    if _NOT_A_STREET.search(candidate):
        return None
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


_BRAND = re.compile(
    r"\b(bradford|rheem|navien|rinnai|whirlpool|kenmore|carrier|trane|lennox|goodman|"
    r"ruud|noritz|honeywell|ecobee|ao smith|american standard)\b",
    re.I,
)
_APPLIANCE_WORD = re.compile(
    r"\b(water heater|furnace|dishwasher|refrigerator|fridge|washer|dryer|thermostat|"
    r"boiler|compressor|condenser|disposal|toilet|faucet|heater)\b",
    re.I,
)


def _name_allowed(candidate: str, *, framed: bool = False) -> bool:
    if not _plausible_name(candidate):
        return False
    if _APPLIANCE_WORD.search(candidate):
        return False
    if framed:
        return True
    if _BRAND.search(candidate):
        return False
    last = candidate.split()[-1]
    if re.fullmatch(STREET_SUFFIX, last, flags=re.I):
        return False
    return True


def _bare_name_blocked(text: str) -> bool:
    """A street, a phone, a ZIP, a brand, or an appliance is not a caller's name."""
    if extract_street(text):
        return True
    if extract_phone(text)[0]:
        return True
    if extract_zip(text):
        return True
    if _BRAND.search(text) or _APPLIANCE_WORD.search(text):
        return True
    return False


def _clean_pair(text: str) -> str | None:
    pairs = re.findall(r"\b([A-Z][a-z]+(?:['-][A-Z][a-z]+)?)\s+([A-Z][a-z]+(?:['-][A-Z][a-z]+)?)\b", text)
    for first, last in pairs:
        candidate = f"{first} {last}"
        if _name_allowed(candidate) and not _APPLIANCE_WORD.search(candidate):
            return candidate
    return None


def _person_name_rejected(candidate: str, issue: str | None = None) -> bool:
    """A verb, a gerund, or a copy of the problem is not a caller's name."""
    for token in (candidate or "").split():
        low = token.lower().strip("'-")
        if low in {
            "send",
            "smell",
            "smells",
            "leaking",
            "dripping",
            "running",
            "coming",
            "going",
            "replace",
            "install",
            "someone",
            "something",
            "crackling",
            "sizzling",
            "burning",
        }:
            return True
        if len(low) >= 6 and low.endswith("ing"):
            return True
    if issue and candidate and candidate.lower() in issue.lower():
        return True
    return False


def extract_introduced_name(text: str) -> str | None:
    match = re.search(
        r"\b(?:my name is|this is|i am|i'm|im|it is|it's)\s+([^\W\d_](?:[^\W\d_]|['-])*(?:\s+[^\W\d_](?:[^\W\d_]|['-])*){0,3})",
        text,
        re.I,
    )
    if not match:
        return None
    chunk = match.group(1)
    chunk = re.split(
        r"\b(?:and|but|at|from|in|on|my|calling|need|have|with|the|phone|i|please|cancel|reschedule|appointment|about|number|not)\b",
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
    if _person_name_rejected(candidate):
        return None
    return candidate


_MARKUP_TAG = re.compile(r"<[^>]*>", re.I)
_MARKUP_TOKEN = {
    "script",
    "alert",
    "javascript",
    "onerror",
    "onclick",
    "iframe",
    "svg",
    "img",
    "src",
    "href",
}


def _without_markup(text: str) -> str:
    return _MARKUP_TAG.sub(" ", text or "")


def _markup_tokens(text: str) -> bool:
    cleaned = "".join(char if (char.isalpha() or char in " '-") else " " for char in _without_markup(text))
    tokens = [part.lower() for part in cleaned.split() if part]
    return bool(tokens) and all(part in _MARKUP_TOKEN for part in tokens)


def _not_a_person_name(text: str) -> bool:
    """A phone, ZIP, street, or markup fragment is not a caller's name."""
    raw = _without_markup(text or "")
    if not raw.strip():
        return True
    if extract_street(raw) or extract_phone(raw)[0] or extract_zip(raw):
        return True
    if _markup_tokens(text or ""):
        return True
    return False


def guess_bare_name(text: str, framed: bool = False) -> str | None:
    """A name frame, or the answer to the name question, may use a brand or a street word."""
    if _not_a_person_name(text):
        return None
    text = _without_markup(text)
    introduced = extract_introduced_name(text)
    if introduced and _name_allowed(introduced, framed=True):
        return introduced
    if extract_street(text) or extract_phone(text)[0] or extract_zip(text):
        return None
    if not framed and _bare_name_blocked(text):
        return None
    if framed and _APPLIANCE_WORD.search(text or "") and introduced is None:
        return None
    trailing = re.findall(r"\b([A-Z][a-z]+(?:['-][A-Z][a-z]+)?)\s+([A-Z][a-z]+(?:['-][A-Z][a-z]+)?)\b", text or "")
    if trailing:
        first, last = trailing[-1]
        candidate = f"{first} {last}"
        if _name_allowed(candidate, framed=framed):
            return candidate
    cleaned = "".join(char if (char.isalpha() or char in " '-") else " " for char in (text or "")).strip()
    parts = [part for part in cleaned.split() if part]
    if not 2 <= len(parts) <= 3:
        return None
    if any(part.lower() in NAME_STOP for part in parts):
        return None
    candidate = " ".join(_proper_token(part) for part in parts)
    if not _name_allowed(candidate, framed=framed):
        return None
    return candidate


def fallback_name(text: str) -> str:
    """A last-resort name. Empty when the utterance is a phone, ZIP, address, or markup."""
    if _not_a_person_name(text):
        return ""
    cleaned = "".join(char if (char.isalpha() or char in " '-") else " " for char in _without_markup(text or ""))
    tokens = [
        part
        for part in cleaned.split()
        if part and part.lower() not in NAME_STOP and part.lower() not in _MARKUP_TOKEN and len(part) > 1
    ]
    if len(tokens) < 2:
        raw = " ".join(_without_markup(text or "").split())
        if raw and not any(char.isdigit() for char in raw):
            letters = "".join(char if char.isalpha() or char in " '-" else " " for char in raw).strip()
            if not letters:
                return "Caller"
        return ""
    candidate = " ".join(_proper_token(part) for part in tokens[:3])
    if not _plausible_name(candidate) or _person_name_rejected(candidate):
        return ""
    return candidate


_FIELD_INSTRUCTION = re.compile(
    r"\b(ignore (?:all |any )?(?:previous|prior|above) instructions|"
    r"treat (?:this|it) as|mark (?:this|it) as|classify (?:this|it)|"
    r"you are now|system prompt|page the on-call|send the on-call|"
    r"disregard (?:the |your )?(?:rules|instructions)|new instructions)\b",
    re.I,
)
FIELD_PHASES = {
    "collect_name",
    "collect_phone",
    "collect_address",
    "collect_zip",
    "offer",
    "confirm",
    "quote_decision",
    "confirm_cancel",
}


def strip_field_instructions(text: str) -> str:
    """A name or address is data. Instruction-like sentences in it are dropped."""
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    kept = [part.strip() for part in parts if part.strip() and not _FIELD_INSTRUCTION.search(part)]
    return " ".join(kept).strip()


def extract_caller_name(turns: list[str], asked_field: str | None, current: str) -> str | None:
    """Name comes from the answer to the name prompt, or from an introduction.

    A turn that is a street, a phone, a ZIP, a brand, or an appliance does not
    donate a bare guess.
    """
    if asked_field == "name":
        found = guess_bare_name(current, framed=True)
        if found and not _person_name_rejected(found):
            return found
        found = _clean_pair(current)
        if found and not _person_name_rejected(found):
            return found
    for turn in reversed(turns):
        introduced = extract_introduced_name(turn)
        if introduced and _name_allowed(introduced, framed=True) and not _person_name_rejected(introduced):
            return introduced
    return None


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
    norm = _fold_latin(normalize(text))
    if re.search(
        r"\b(earliest|soonest|first one|first available|the first|asap|as soon as possible|"
        r"lo antes posible|cuanto antes|la primera|el primero)\b",
        norm,
    ):
        return 0
    if re.search(r"\b(second|2nd|the other one|middle one)\b", norm):
        return 1
    if re.search(r"\b(third|3rd|the last one|last option)\b", norm):
        return 2
    return None
