"""Hazard concepts, not memorized caller sentences.

A turn is an emergency when a hazard is present and a narrow negation is not
attached to that hazard. Gas, carbon monoxide, sparks, and smoke stand on
their own. Active water needs a force or a backup, not the word "leak".
No heat or no cooling counts when the home is cold or someone vulnerable is
there. The word "emergency" counts unless the caller is saying it is not one.
"""

from __future__ import annotations

import re
import unicodedata

_NEGATED = re.compile(
    r"\b(?:no|not|without|don't|dont|do not|sin|no hay|isn't|isnt|nothing)\b"
    r"(?:\s+(?:a|an|any|the|just|really|even|of)){0,2}\s+"
    r"(?:gas|smell|odor|odour|leak|sparks?|sewage|humo|olor)\b",
    re.I,
)
_HISTORICAL = re.compile(
    r"\b(last year|last winter|last month|last week|years ago|months ago|"
    r"already fixed|was fixed|were fixed|already repaired|got it fixed|"
    r"we fixed|used to|was already|had already|already stopped)\b",
    re.I,
)
_CURRENT = re.compile(
    r"\b(right now|won't stop|wont stop|will not stop|can't stop|cant stop|"
    r"won't shut|wont shut|will not shut|smell|smelling|odor|odour|gushing|pouring|"
    r"shooting|spraying|spewing|sparks?|sparking|hissing|beeping|now)\b",
    re.I,
)
_PRESENT_VERB = re.compile(
    r"\b(is|are|'s|smell|smelling|hissing|pouring|gushing|spraying|spewing|"
    r"beeping|sparking|smoking|won't|wont|coming up|right now)\b",
    re.I,
)
_GAS_BILL = re.compile(r"\bgas\s+(?:bill|invoice|utility|company)\b", re.I)
_GAS_APPLIANCE = re.compile(r"\bgas\s+(?:water heater|furnace|stove|range|dryer|fireplace)\b", re.I)
_GAS_SIGNAL = re.compile(
    r"\b(smell|smells|smelling|odor|odour|leak|leaking|hiss|hissing|rotten|sulfur|sulphur|"
    r"fuerte|olor|huele|huelen|azufre)\b",
    re.I,
)
_GAS_WORD = re.compile(
    r"\b(gas|propane|natural gas|rotten eggs?|sulfur|sulphur|huevo podrido|azufre)\b",
    re.I,
)
_CO_NAME = re.compile(
    r"\b(carbon monoxide|monoxido(?: de carbono)?|co alarm|co detector|co2 alarm)\b|\bco\b",
    re.I,
)
_CO_HARD = re.compile(
    r"\b(going off|won't stop|wont stop|will not stop|screaming|beeping|beeps|"
    r"sin parar|sounding|ppm)\b",
    re.I,
)
_CO_BATTERY_ISSUE = re.compile(
    r"\b(chirp\w*|replace\w*|swap\w*|needs?|necesit\w*|cambiar|solo|only|low|dead|pila|pilas)\b",
    re.I,
)
_CO_PARTS_ERRAND = re.compile(r"\b(bring|parts|faucet|install|quote|buy|purchase)\b", re.I)
_CO_BATTERY = re.compile(r"\b(battery|batteries|pila|pilas)\b", re.I)
_SYMPTOM = re.compile(
    r"\b(headaches?|dizzy|dizziness|nauseous|nauseated|nausea|vomit\w*|"
    r"throwing up|feels? sick|passed out|confused)\b",
    re.I,
)
_HEAT_SOURCE = re.compile(r"\b(furnace|heater|boiler|gas|carbon|monoxido)\b", re.I)
_WATER_FORCE = re.compile(
    r"\b(pouring|gushing|shooting|spraying|flooding|flooded|inundand\w*|inundad\w*|"
    r"burst|busted|won't stop|wont stop|will not stop|won't shut|wont shut|will not shut|"
    r"can't shut|cant shut|shut off|feet of water|agua por todas|saliendo|no para|sin parar|chorro)\b",
    re.I,
)
_WATER_NOUN = re.compile(
    r"\b(water|agua|pipe|pipes|line|ceiling|wall|basement|garage|sewage|sewer|"
    r"alcantarill\w*)\b",
    re.I,
)
_WATER_PATH = re.compile(
    r"\b(coming|shooting|pouring|gushing|running|saliendo|sale)\b.{0,24}\b(wall|ceiling|floor|techo)\b|"
    r"\b(wall|ceiling|floor|techo)\b.{0,24}\b(coming|pouring|gushing|through|water|agua|saliendo)\b",
    re.I,
)
_SEWAGE = re.compile(r"\b(sewage|sewer|raw sewage|alcantarill\w*|poop water|agua negra)\b", re.I)
_SEWAGE_MOTION = re.compile(r"\b(backup|backing|backed|coming|overflow|subiendo|regres)\w*\b", re.I)
_ELECTRICAL = re.compile(
    r"\b(sparks?|sparking|chispas?|arcing|electrical fire)\b|"
    r"\b(outlet|socket|breaker|wire|wiring|panel|switch|fixture|plug|cord|light)\b.{0,40}"
    r"\b(smoke|smoking|popping|burning|melting|hot|warm|humo|sparks?)\b|"
    r"\b(smoke|smoking|popping|burning smell|burning plastic|humo|sparks?|melting)\b.{0,40}"
    r"\b(outlet|socket|breaker|wire|wiring|panel|switch|fixture|plug|cord|light)\b",
    re.I,
)
_COOKING = re.compile(r"\b(toast|cooking|food|oven baking|burnt toast)\b", re.I)
_COMFORT = re.compile(
    r"\b(no heat|without heat|lost (?:the )?heat|"
    r"heat(?:'s| is| went| has gone| is gone)? out|"
    r"heat(?:'s| is)? not working|heater (?:won't|wont|will not) (?:come|turn) on|"
    r"furnace (?:quit|died|is dead|is out|out|went out|won't come on|wont come on|is not working|isn't working)|"
    r"heater (?:quit|died|is dead|broke|broken|is not working|isn't working|stopped)|"
    r"heat died|(?:isn't|isnt|not) heating|"
    r"no ac\b|no a/c|no cooling|(?:isn't|isnt|not) cooling|"
    r"ac (?:quit|died|is out|out|went out|stopped|broke|broken)|"
    r"air condition(?:er|ing) (?:quit|died|is dead|is out|out|went out|broke|broken|stopped|is not working)|"
    r"cooling (?:quit|died|is out|went out|broke|stopped)|"
    r"sin calor|no hay calor|no hay calef|calefaccion no)\b",
    re.I,
)
_AGE = re.compile(
    r"\b(\d{2,3})\s*(?:years?\s*old|year-old|yo)\b|"
    r"\bi(?:'m| am)\s+(\d{2,3})\b|"
    r"\bis\s+(\d{2,3})\b(?!\s*(?:degrees|degree|grados|°))",
    re.I,
)
_OVER_UNDER = re.compile(r"\b(?:over|above|under|below)\s+(\d{2,3})\b", re.I)
_FIXTURE = re.compile(
    r"\bemergency\s+(?:shut-?off|valve|stop|cutoff|cut-off)\b",
    re.I,
)
_VULNERABLE = re.compile(
    r"\b(elderly|infant|newborn|baby|babies|toddler|pregnant|oxygen|"
    r"grandma|grandpa|grandmother|grandfather|year-old|years old|"
    r"bebe|bebé|ancian\w*|abuela|abuelo|niño|nino|niña|nina)\b",
    re.I,
)
_FREEZING = re.compile(r"\b(freezing|freeze|shivering|hypotherm\w*|congel\w*)\b", re.I)
_DEGREES = re.compile(r"\b(\d{1,3})\s*(?:degrees|degree|grados|°f|°)\b", re.I)
_EMERGENCY_WORD = re.compile(r"\bemergenc(?:y|ia)\b", re.I)
_NOT_EMERGENCY = re.compile(
    r"\b(not an emergency|no emergency|isn't an emergency|isnt an emergency|"
    r"non-emergency|not urgent|no es una emergencia)\b",
    re.I,
)


def fold(text: str) -> str:
    cleaned = (text or "").replace("’", "'").replace("—", " ").replace("–", " ")
    decomposed = unicodedata.normalize("NFKD", cleaned)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    stripped = stripped.lower()
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return stripped


def _clauses(text: str) -> list[str]:
    parts = re.split(r"[.;!?]|\bbut\b|\balthough\b|\bpero\b", text)
    return [part.strip() for part in parts if part.strip()]


_STRONG_NOW = re.compile(
    r"\b(won't stop|wont stop|will not stop|pouring|gushing|spraying|spewing|hissing|"
    r"smell|smelling|odor|odour|beeping|sparking|right now|ahora|sin parar)\b",
    re.I,
)
_GAS_I18N = re.compile(
    r"\b(gaz|gas|ga)\b.{0,32}\b(odeur|cheiro|cheira|mui|amoy|olor|huele|fuite|vazamento|leak)\b|"
    r"\b(odeur|cheiro|cheira|mui|amoy|olor|huele|fuite|vazamento)\b.{0,32}\b(gaz|gas|ga)\b|"
    r"\b(oeuf pourri|ovo podre|trung thoi|bulok na itlog|huevo podrido|sent le gaz)\b",
    re.I,
)
_WATER_I18N = re.compile(
    r"\b(inonde\w*|alagand\w*|alagado|ngap|bumabaha|baha|sumabog|vazando|tagas|estourou)\b",
    re.I,
)


def _skip_clause(clause: str) -> bool:
    """A finished event stays routine unless a hazard is happening in the same breath."""
    if _HISTORICAL.search(clause) and not _STRONG_NOW.search(clause):
        return True
    return False


def _negated_at(clause: str, index: int) -> bool:
    """True when a negation word governs the token at index, not a hedge or a 'no,' restart."""
    window = clause[max(0, index - 42):index]
    window = re.sub(r"^.*\bno\s*,", "", window)
    if re.search(r"[,;]\s*$", window):
        return False
    words = re.findall(r"[a-z0-9']+", window.lower())
    tail = words[-5:]
    if {"sure", "idea", "certain"} & set(tail):
        return False
    negations = {"no", "not", "without", "sin", "isn't", "isnt", "nothing", "never", "dont"}
    return any(word in negations for word in tail)


def _unnegated(clause: str, pattern: re.Pattern[str]) -> bool:
    return any(not _negated_at(clause, match.start()) for match in pattern.finditer(clause))


def _gas(clause: str) -> bool:
    if re.search(r"\b(car|vehicle|truck|gas station|out of gas|ran out of gas)\b", clause):
        return False
    if re.search(r"\b(convert|conversion|hook ?up)\b", clause) and not _GAS_SIGNAL.search(clause):
        return False
    foreign = _GAS_I18N.search(clause)
    if foreign and not _negated_at(clause, foreign.start()):
        return True
    odor = re.search(r"\b(rotten eggs?|huevo podrido|sulfur|sulphur|azufre)\b", clause)
    if odor and not _negated_at(clause, odor.start()):
        return True
    if re.search(r"\b(huele|huelen|olor)\b.{0,24}\bgas\b|\bgas\b.{0,24}\b(huele|olor)\b", clause):
        smell = re.search(r"\b(huele|huelen|olor)\b", clause)
        if smell and not _negated_at(clause, smell.start()):
            return True
    stripped = _NEGATED.sub(" ", clause)
    negated = stripped != clause
    if _GAS_WORD.search(stripped) and (
        _GAS_SIGNAL.search(stripped) or re.search(r"\bgas\s+leak\b|\bleak(?:ing)?\s+gas\b", stripped)
    ):
        return True
    if negated:
        return False
    if not _GAS_WORD.search(clause):
        return False
    if _GAS_BILL.search(clause) or _GAS_APPLIANCE.search(clause):
        return False
    # Bare "gas" is not a leak. Odor, hiss, or the word leak has to be there.
    return False


def _carbon(clause: str) -> str | None:
    """Return 'advice', 'definite', or None.

    A sounding alarm, a ppm reading, or symptoms with the heat on are definite.
    A battery, a chirp, or "only the battery" is advice. Bringing a battery
    along on a faucet job is neither.
    """
    named = bool(_CO_NAME.search(clause))
    symptom = _SYMPTOM.search(clause)
    symptoms = bool(symptom and _HEAT_SOURCE.search(clause) and not _negated_at(clause, symptom.start()))
    if symptoms or re.search(r"\b\d+\s*ppm\b", clause):
        return "definite"
    if (
        symptom
        and re.search(r"\b(detector|alarm)\b", clause)
        and _unnegated(clause, _CO_HARD)
    ):
        return "definite"
    hard = _unnegated(clause, _CO_HARD)
    chirp = _unnegated(clause, re.compile(r"\b(chirp\w*|pitando|pita|pito)\b", re.I))
    if _CO_BATTERY.search(clause) and (named or chirp or _CO_BATTERY_ISSUE.search(clause)):
        if hard:
            return "definite"
        if _CO_PARTS_ERRAND.search(clause) and not _CO_BATTERY_ISSUE.search(clause) and not chirp:
            return None
        return "advice"
    if named and (hard or chirp):
        return "definite"
    if named and re.search(r"\b(install|quote|buy|purchase)\b", clause):
        return None
    return None


def _sewage_active(clause: str) -> bool:
    if not _SEWAGE.search(clause):
        return False
    motions = list(_SEWAGE_MOTION.finditer(clause))
    if motions:
        return any(not _negated_at(clause, match.start()) for match in motions)
    return bool(re.search(r"\b(raw sewage|agua negra)\b", clause))


def _water(clause: str) -> bool:
    if _sewage_active(clause):
        return True
    foreign = _WATER_I18N.search(clause)
    if foreign and not _negated_at(clause, foreign.start()):
        return True
    path = _WATER_PATH.search(clause)
    if path and not _negated_at(clause, path.start()):
        return True
    force = next(
        (match for match in _WATER_FORCE.finditer(clause) if not _negated_at(clause, match.start())),
        None,
    )
    if force and (_WATER_NOUN.search(clause) or re.search(r"\b(burst|flood)\b", clause)):
        return True
    burst = re.search(r"\bpipe\b.{0,24}\bburst\b|\bburst\b.{0,24}\bpipe\b|\btank\b.{0,16}\bsplit\b", clause)
    if burst and not _negated_at(clause, burst.start()):
        return True
    return False


def _electrical(clause: str) -> bool:
    if _COOKING.search(clause) and not re.search(r"\b(outlet|panel|breaker|wire)\b", clause):
        return False
    return _unnegated(clause, _ELECTRICAL)


def _older_adult(clause: str) -> bool:
    for match in _AGE.finditer(clause):
        raw = next((group for group in match.groups() if group), None)
        if raw and int(raw) >= 65:
            return True
    return False


_COMFORT_ALT = re.compile(
    r"\b(heater|furnace|heat|heating|ac|a/c|air|cooling)\b.{0,36}"
    r"\b(not working|stopped|broke|broken|won't come on|wont come on|will not come on|"
    r"won't turn on|wont turn on|will not turn on|isn't heating|isnt heating|isn't cooling|isnt cooling)\b",
    re.I,
)


def _comfort(clause: str, full: str | None = None) -> bool:
    if not (_COMFORT.search(clause) or _COMFORT_ALT.search(clause)):
        return False
    blob = full or clause
    if _VULNERABLE.search(blob) or _FREEZING.search(blob) or _older_adult(blob):
        return True
    for match in _DEGREES.finditer(blob):
        value = int(match.group(1))
        if value <= 50 or value >= 90:
            return True
    for match in _OVER_UNDER.finditer(blob):
        value = int(match.group(1))
        if match.group(0).lower().startswith(("over", "above")) and value >= 90:
            return True
        if match.group(0).lower().startswith(("under", "below")) and value <= 45:
            return True
    return False


def _emergency_word(clause: str) -> bool:
    if _NOT_EMERGENCY.search(clause):
        return False
    if re.search(r"\b(fee|charge|how much|price|cost|do you do)\b", clause):
        return False
    if re.search(r"\bonly emergency\b", clause):
        return False
    stripped = _FIXTURE.sub(" ", clause)
    found = False
    for match in _EMERGENCY_WORD.finditer(stripped):
        if not _negated_at(stripped, match.start()):
            found = True
    return found


def classify_emergency(text: str) -> tuple[str, str | None]:
    """Return ('definite'|'advice'|'none', label).

    'definite' transfers. 'advice' is the carbon-monoxide battery case.
    Historical clauses are ignored. A negation has to sit on the hazard.
    """
    folded = fold(text)
    advice = _battery_advice(folded)
    for clause in _clauses(folded):
        if _skip_clause(clause):
            continue
        if _gas(clause):
            return "definite", "Gas"
        carbon = _carbon(clause)
        if carbon == "definite":
            return "definite", "Carbon monoxide"
        if carbon == "advice":
            advice = True
        if _electrical(clause):
            return "definite", "Electrical hazard"
        if _water(clause):
            return "definite", "Active water"
        if _comfort(clause, folded):
            return "definite", "Unsafe indoor temperature"
        if _emergency_word(clause):
            return "definite", "Caller said emergency"
    ruled: tuple[str, str | None]
    if advice:
        ruled = ("advice", "CO detector battery")
    elif _backup(folded) >= 3:
        ruled = ("definite", "Hazard signals")
    else:
        ruled = ("none", None)
    if ruled[0] != "definite" and _routine_context(folded):
        return "none", None
    from app.agent.hazard_embed import embed_hazard

    guessed = embed_hazard(folded)
    if guessed[1] == "Unsafe indoor temperature" and not _comfort_context(folded):
        guessed = ("none", None)
    return _stricter(ruled, guessed)


def _comfort_context(text: str) -> bool:
    """No heat or no cooling is urgent only with a vulnerable person or an extreme temperature."""
    if _VULNERABLE.search(text) or _FREEZING.search(text) or _older_adult(text):
        return True
    for match in _DEGREES.finditer(text):
        value = int(match.group(1))
        if value <= 50 or value >= 90:
            return True
    for match in _OVER_UNDER.finditer(text):
        value = int(match.group(1))
        if match.group(0).lower().startswith(("over", "above")) and value >= 90:
            return True
        if match.group(0).lower().startswith(("under", "below")) and value <= 45:
            return True
    return False


def _battery_advice(text: str) -> bool:
    """A chirp plus a battery, even split across two sentences, is not a page."""
    chirp = re.search(r"\b(chirp\w*|pita\w*|pito)\b", text)
    if not chirp or not _CO_BATTERY.search(text):
        return False
    if _SYMPTOM.search(text) or _unnegated(text, _CO_HARD):
        return False
    return True


def _routine_context(text: str) -> bool:
    """Fee questions, appliance conversions, and a car with no fuel are not pages."""
    if _HISTORICAL.search(text) and not _STRONG_NOW.search(text):
        return True
    if re.search(r"\b(car|vehicle|truck|gas station|out of gas|ran out of gas)\b", text) and not _GAS_SIGNAL.search(text):
        return True
    if re.search(r"\b(convert|conversion|hook ?up)\b", text) and not _GAS_SIGNAL.search(text):
        return True
    if _GAS_APPLIANCE.search(text) and not _GAS_SIGNAL.search(text) and not _GAS_I18N.search(text):
        return True
    if _GAS_BILL.search(text) and not _GAS_SIGNAL.search(text):
        return True
    if (
        re.search(r"\b(install|quote|buy|purchase)\b", text)
        and _CO_NAME.search(text)
        and not _CO_HARD.search(text)
        and not _SYMPTOM.search(text)
    ):
        return True
    if re.search(r"\b(fee|charge|how much|price|cost)\b", text) and _EMERGENCY_WORD.search(text):
        if not _GAS_SIGNAL.search(text) and not _ELECTRICAL.search(text) and not _WATER_FORCE.search(text):
            return True
    if re.search(r"\b(only emergency|wallet|not an emergency)\b", text) and not _GAS_SIGNAL.search(text):
        if not _ELECTRICAL.search(text) and not _WATER_FORCE.search(text) and not _COMFORT.search(text):
            return True
    return False


_RANK = {"none": 0, "advice": 1, "ask": 2, "definite": 3}


def _stricter(left: tuple[str, str | None], right: tuple[str, str | None]) -> tuple[str, str | None]:
    if _RANK.get(right[0], 0) > _RANK.get(left[0], 0):
        return right
    return left


def _backup(text: str) -> int:
    """Lightweight bag of stems. It only adds a transfer; it cannot clear one."""
    score = 0
    for clause in _clauses(text):
        if _skip_clause(clause):
            continue
        score += _backup_clause(clause)
    return score


def _backup_clause(clause: str) -> int:
    score = 0
    remaining = _NEGATED.sub(" ", clause)
    if re.search(r"\b(gas|propane)\b", remaining) and _GAS_SIGNAL.search(remaining):
        score += 3
    if _unnegated(clause, re.compile(r"\b(sparks?|sparking|chispas)\b", re.I)):
        score += 3
    if _sewage_active(clause):
        score += 3
    if _unnegated(clause, re.compile(r"\b(flooding|gushing|inundand\w*)\b", re.I)) and (
        _WATER_NOUN.search(clause) or re.search(r"\b(basement|garage|house|casa|floor|ceiling|home)\b", clause)
    ):
        score += 3
    if _SYMPTOM.search(clause) and _HEAT_SOURCE.search(clause):
        score += 3
    if _COMFORT.search(clause) and (_VULNERABLE.search(clause) or _FREEZING.search(clause)):
        score += 3
    return score
