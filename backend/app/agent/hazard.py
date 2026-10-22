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
    r"\b(?:no|not|without|don't|dont|do not|sin|no hay|isn't|isnt|nothing|nahi|nahin)\b"
    r"(?:\s+(?:a|an|any|the|just|really|even|of)){0,2}\s+"
    r"(?:gas|smells?|smelling|odor\w*|odour\w*|stinks?|stinking|reeks?|reeking|"
    r"whiff\w*|fumes?|leak\w*|sparks?|sewage|humo|olor)\b",
    re.I,
)
_HISTORICAL = re.compile(
    r"\b(last year|last winter|last month|last week|years ago|months ago|"
    r"already fixed|was fixed|were fixed|already repaired|got it fixed|"
    r"we fixed|used to|was already|had already|already stopped|"
    r"last summer|last fall|last autumn|last spring|over the winter|during the winter|"
    r"this past winter|previous winter|was serviced|had it serviced|seasonal maintenance)\b",
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
    r"stink\w*|reek\w*|whiff\w*|fumes?|"
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
    r"sin parar|sounding|sonando|suena|sonar|ppm)\b",
    re.I,
)
_CO_BATTERY_ISSUE = re.compile(
    r"\b(chirp\w*|replace\w*|swap\w*|needs?|necesit\w*|cambiar|solo|only|low|dead|pila|pilas)\b",
    re.I,
)
_CO_PARTS_ERRAND = re.compile(r"\b(bring|parts|faucet|install|quote|buy|purchase)\b", re.I)
_CO_BATTERY = re.compile(r"\b(battery|batteries|pila|pilas)\b", re.I)
_SYMPTOM = re.compile(
    r"\b(headaches?|dizzy|dizziness|woozy|wooziness|nauseous|nauseated|nausea|vomit\w*|"
    r"throwing up|feels? sick|passed out|confused|"
    r"maread\w*|mareo|aturdid\w*|desmay\w*|confundid\w*|vomito)\b|"
    r"\bdolor de cabeza\b",
    re.I,
)
_EXPOSURE = re.compile(
    r"\b(headaches?|dizzy|dizziness|woozy|wooziness|nauseous|nauseated|nausea|vomit\w*|"
    r"throwing up|feels? sick|feeling sick|passed out|confused|sleepy|drowsy|sick|"
    r"maread\w*|mareo|aturdid\w*|desmay\w*|confundid\w*|vomito|enferm\w*|"
    r"adormilad\w*|somnolient\w*)\b|"
    r"\bdolor de cabeza\b|"
    r"\beyes\b.{0,20}\b(water\w*|burn\w*|sting\w*|llor\w*|aguad\w*|ard\w*)\b|"
    r"\b(watery|watering|llorosos)\s+eyes\b",
    re.I,
)
_HEAT_SOURCE = re.compile(r"\b(furnace|heater|boiler|gas|carbon|monoxido)\b", re.I)
_WATER_FORCE = re.compile(
    r"\b(pouring|gushing|shooting|spraying|spewing|spurting|jetting|blasting|erupting|"
    r"cascading|geyser(?:ing)?|scalding|scalds?|"
    r"flooding|flooded|inundand\w*|inundad\w*|inundacion\w*|"
    r"burst|busted|won't stop|wont stop|will not stop|won't shut|wont shut|will not shut|"
    r"can't shut|cant shut|shut off|feet of water|agua por todas|saliendo|no para|sin parar|chorro)\b",
    re.I,
)
_WATER_NOUN = re.compile(
    r"\b(water|agua|pipe|pipes|line|ceiling|wall|basement|garage|sewage|sewer|"
    r"alcantarill\w*|piso|sotano|sotanos)\b",
    re.I,
)
_WATER_PATH = re.compile(
    r"\b(coming|shooting|pouring|gushing|running|saliendo|sale)\b.{0,24}\b(wall|ceiling|floor|techo)\b|"
    r"\b(wall|ceiling|floor|techo)\b.{0,24}\b(coming|pouring|gushing|through|water|agua|saliendo)\b",
    re.I,
)
_SEWAGE = re.compile(
    r"\b(sewage|sewer|raw sewage|sewer water|wastewater|brown water|black water|"
    r"alcantarill\w*|poop water|aguas? negras)\b",
    re.I,
)
_SEWAGE_MOTION = re.compile(r"\b(backup|backing|backed|coming|overflow|subiendo|regres)\w*\b", re.I)
_ELECTRICAL = re.compile(
    r"\b(sparks?|sparking|chispas?|arcing|electrical fire)\b|"
    r"\b(outlet|socket|breaker|wire|wiring|panel|switch|fixture|plug|cord|light)\b.{0,40}"
    r"\b(smoke|smoking|popping|burning|melting|melted|hot|scorch\w*|charred|humo|sparks?)\b|"
    r"\b(smoke|smoking|popping|burning smell|burning plastic|humo|sparks?|melting|melted|scorch\w*|charred)\b.{0,40}"
    r"\b(outlet|socket|breaker|wire|wiring|panel|switch|fixture|plug|cord|light)\b",
    re.I,
)
_COOKING = re.compile(r"\b(toast|cooking|food|oven baking|burnt toast)\b", re.I)
_COMFORT = re.compile(
    r"\b(no heat|without heat|lost (?:the )?heat|"
    r"heat(?:'s| is| went| has gone| is gone)? out|"
    r"heat(?:'s| is)? not working|heater (?:won't|wont|will not) (?:come|turn) on|"
    r"furnace (?:quit|died|is dead|dead|is out|out|went out|won't come on|wont come on|is not working|isn't working)|"
    r"heater (?:quit|died|is dead|dead|broke|broken|is not working|isn't working|stopped)|"
    r"boiler (?:quit|died|is dead|dead|is out|out|went out|won't come on|is not working)|"
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
    r"\bi(?:'m| am)\s+(\d{2,3})\b(?!\s*(?:degrees|degree|grados|°|inside|indoors))|"
    r"\b(?:who|she|he|mom|dad|mother|father|grandma|grandpa|grandmother|grandfather) is\s+(\d{2,3})\b",
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
_BARE_TEMP = re.compile(
    r"\b(?:it(?:'s| is)|inside|indoors)\s+(\d{2,3})\b(?!\s*(?:years?|dollars?|bucks|percent|%))",
    re.I,
)
_HYPOTHETICAL = re.compile(
    r"\b(just asking|hypothetically|hypothetical|what if|how fast|how soon)\b",
    re.I,
)
_EMERGENCY_WORD = re.compile(r"\bemergenc(?:y|ia)\b", re.I)
_NOT_EMERGENCY = re.compile(
    r"\b(not an emergency|no emergency|isn't an emergency|isnt an emergency|"
    r"non-emergency|not urgent|no es una emergencia)\b",
    re.I,
)


def fold(text: str) -> str:
    """Lowercase for the rules. Latin accents fold. Hangul syllables stay intact."""
    cleaned = (text or "").replace("’", "'").replace("—", " ").replace("–", " ")
    pieces: list[str] = []
    for char in cleaned:
        code = ord(char)
        if 0x1100 <= code <= 0x11FF or 0xAC00 <= code <= 0xD7AF:
            pieces.append(char)
            continue
        decomposed = unicodedata.normalize("NFKD", char)
        pieces.append("".join(item for item in decomposed if not unicodedata.combining(item)))
    stripped = "".join(pieces).lower()
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return stripped


# Tokens that are not words. Real words such as hose, small, and mouse stay put.
_TYPO_TOKEN = {
    "smel": "smell",
    "smeel": "smell",
    "smelg": "smell",
    "hous": "house",
    "watr": "water",
    "wter": "water",
    "leakin": "leaking",
    "leakn": "leaking",
    "thru": "through",
    "outlit": "outlet",
    "outlett": "outlet",
    "pannel": "panel",
    "panal": "panel",
    "dizzey": "dizzy",
    "dizzie": "dizzy",
    "dizy": "dizzy",
    "sleeppy": "sleepy",
    "boillin": "boiling",
    "boilling": "boiling",
    "boilin": "boiling",
    "burnin": "burning",
    "flickrin": "flickering",
    "flickerin": "flickering",
    "electricty": "electricity",
    "electrcity": "electricity",
    "fixtur": "fixture",
    "alaram": "alarm",
    "alrm": "alarm",
    "steem": "steam",
    "vapur": "vapor",
    "oder": "odor",
    "gass": "gas",
    "heatar": "heater",
    "monoxid": "monoxide",
    "carbom": "carbon",
    "detctor": "detector",
    "detecter": "detector",
    "boiller": "boiler",
    "reccessed": "recessed",
    "recesed": "recessed",
    "instal": "install",
    "instll": "install",
    "replacment": "replacement",
    "watring": "watering",
    "scaldin": "scalding",
    "smelll": "smell",
    "housr": "house",
}
_GLOSS = (
    (re.compile(r"\b(alarma|detector)\s+de\s+humo\b"), r"\1 de humo smoke alarm"),
    (re.compile(r"\bducha\s+de\s+vapor\b"), "ducha de vapor steam shower"),
    (re.compile(r"\b(vapor|vaho)\b"), r"\1 steam"),
    (re.compile(r"\b(herv\w*|hirv\w*|hierv\w*|ebull\w*)\b"), r"\1 boiling"),
    (re.compile(r"\b(quemad\w*|quemando)\b"), r"\1 burning"),
    (re.compile(r"\bcasi\b"), "casi almost"),
    (re.compile(r"\b(quema|quemo|quemarse)\b"), r"\1 burned"),
    (re.compile(r"\b(hijo|hija|nino|nina|bebe|criatura)\b"), r"\1 child"),
    (re.compile(r"\b(lampara|foco)\b"), r"\1 light fixture"),
    (re.compile(r"\bluz\b"), "luz light"),
    (re.compile(r"\b(parpade\w*|titila\w*)\b"), r"\1 flicker"),
    (re.compile(r"\bgote\w*\b"), lambda match: f"{match.group(0)} dripping water"),
    (re.compile(r"\b(tablero)\b"), r"\1 panel"),
    (re.compile(r"\b(enchufe|tomacorriente)\b"), r"\1 outlet"),
    (re.compile(r"\b(zumb\w*)\b"), r"\1 buzz"),
    (re.compile(r"\b(olor|huele|huelen)\b"), r"\1 smell"),
    (re.compile(r"\bojos\b(.{0,24})\b(llor\w*|aguad\w*|ard\w*)\b"), r"ojos\1\2 eyes watering"),
    (re.compile(r"\b(mareo|maread\w*|enferm\w*|adormilad\w*|somnolient\w*)\b"), r"\1 dizzy sleepy sick"),
    (re.compile(r"\bmonoxido\b"), "monoxido carbon monoxide"),
    (re.compile(r"\balarma\b"), "alarma alarm"),
    (re.compile(r"\bcaldera\b"), "caldera boiler"),
    (re.compile(r"\bvalvula\b"), "valvula valve"),
    (re.compile(r"\bventilador\b"), "ventilador fan"),
    (re.compile(r"\bempotrad\w*\b"), lambda match: f"{match.group(0)} recessed"),
    (re.compile(r"\b(instalar|instalacion|reemplaz\w*|recambio)\b"), r"\1 install replace"),
    (re.compile(r"\b(revision|revisar|mantenimiento|chequeo)\b"), r"\1 check maintenance"),
)
_COMMERCIAL = re.compile(
    r"\b(insurance|insurer|claim|adjuster|premium|"
    r"inspecc\w*|inspection|cotiz\w*|presupuesto)\b",
    re.I,
)
_PRESENT_DANGER = re.compile(
    r"\b(won't stop|wont stop|will not stop|can't shut|cant shut|cannot shut|"
    r"gushing|spewing|jetting|blasting|erupting|cascading|geyser|scalding|"
    r"spraying|shooting|pouring|feet of water|someone is hurt|anyone hurt|"
    r"getting hurt|almost burned|nearly burned|onto the floor|all over the floor)\b",
    re.I,
)
_CLEARED = re.compile(
    r"\b(no leak|not leaking|isn't leaking|isnt leaking|nothing is leaking|no water|"
    r"no smell|do not smell|don't smell|dont smell|no odor|nothing smells|no gas smell|"
    r"not a leak|it can wait|puede esperar|no hay olor|no hay fuga|sin olor|sin fuga)\b",
    re.I,
)
_CATALOGUE = re.compile(
    r"\b(steam\s+shower|shower\s+valve|ducha\s+de\s+vapor)\b|"
    r"\b(bath(?:room)?\s+fan|exhaust\s+fan|vent\s+fan|ventilador)\b|"
    r"\b(fan|ventilador)\b.{0,32}\b(bath|bathroom|bano|banera)\b|"
    r"\b(bath|bathroom|bano|banera)\b.{0,32}\b(fan|ventilador)\b|"
    r"\b(recessed(?:\s+lights?)?|can\s+lights?|luces?\s+empotrad\w*|empotrad\w*)\b|"
    r"\b(smoke\s+alarms?|smoke\s+detectors?|alarma\s+de\s+humo|detector\s+de\s+humo)\b|"
    r"\b(instal\w*|reemplaz\w*|replac\w*|cambiar|poner|comprar|buy|quote)\b.{0,56}"
    r"\b((?:carbon monoxide|monoxido|co)\b.{0,16}\b(?:detector|alarm)s?|(?:detector|alarma)\b.{0,20}\b(?:monoxido|humo|co))\b|"
    r"\b((?:carbon monoxide|monoxido|co)\b.{0,16}\b(?:detector|alarm)s?|(?:detector|alarma)\b.{0,20}\b(?:monoxido|humo))\b.{0,40}"
    r"\b(instal\w*|reemplaz\w*|replac\w*|cambiar|comprar|buy|quote|install)\b|"
    r"\b(boiler|caldera)\b.{0,48}\b(check|service|maintenance|tune|inspect\w*|revision|revisar|mantenimiento|chequeo)\b|"
    r"\b(check|service|maintenance|tune|inspect\w*|revision|revisar|mantenimiento|chequeo)\b.{0,48}\b(boiler|caldera)\b",
    re.I,
)
_APPLIANCE_BASIN = re.compile(
    r"\b(dishwasher|washing machine|clothes washer|\bwashers?\b|fridge|refrigerator|ice ?maker)\b",
    re.I,
)
_LEAVING_APPLIANCE = re.compile(
    r"\b(overflow\w*|onto the floor|on the floor|out of the|across the floor|all over|"
    r"won't stop|wont stop|will not stop|spraying|ceiling)\b",
    re.I,
)
_WATER_MOTION = re.compile(r"\b(water|agua|drip\w*|leak\w*|wet|gote\w*)\b", re.I)
_ELEC_SURFACE = re.compile(
    r"\b(fixture|outlet|socket|receptacle|wiring|electric\w*|light|lamp|luminaire)\b",
    re.I,
)
_FROM_WORD = re.compile(r"\b(from|out of|off of|through|de la|del|desde)\b", re.I)
_STEAM_BOIL = re.compile(r"\b(steam|vapor|vapour|boiling|boil|hirviendo|scald\w*)\b", re.I)
_HURT = re.compile(
    r"\b(almost|nearly|casi|burned|burnt|hurt|scald\w*|quem\w*)\b",
    re.I,
)
_PERSON = re.compile(
    r"\b(child|kid|kids|baby|son|daughter|hijo|hija|he|she|him|her|me|us|person|someone|anybody|anyone|nino|nina)\b",
    re.I,
)
_BURN_SMELL = re.compile(
    r"\b(burning smell|smell of burning|smells? burnt|burnt smell|burning plastic|"
    r"smells? like (?:burning|burnt|plastic)|hot plastic|melted plastic|olor a quemado)\b|"
    r"\bburning\b.{0,20}\b(smell|plastic|rubber)\b|"
    r"\b(smell\w*|olor)\b.{0,20}\b(burning|burnt|burned|quemad\w*)\b",
    re.I,
)
_PANEL_DEVICE = re.compile(r"\b(panel|outlet|socket|receptacle|breaker|tablero|enchufe)\b", re.I)
_DUSTY_SEASON = re.compile(
    r"\b(dusty|burning[- ]dust|warm dust|first (?:cold|heating)|each october|"
    r"every (?:year|winter|fall|october)|when the (?:furnace|heat) (?:starts|kicks))\b",
    re.I,
)
_POPPING = re.compile(
    r"\b(popp\w*|rumbl\w*|kettl\w*)\b.{0,48}\b(water heater|heater|boiler|tank|calentador|caldera)\b|"
    r"\b(water heater|heater|boiler|tank|calentador|caldera)\b.{0,48}\b(popp\w*|rumbl\w*|kettl\w*)\b",
    re.I,
)
_PILOT_OUT = re.compile(
    r"\bpilot\b.{0,40}\b(keeps going out|goes out|keeps dying|won't stay|wont stay|will not stay|no se queda)\b|"
    r"\b(keeps going out|goes out|keeps dying)\b.{0,24}\bpilot\b",
    re.I,
)
_BASE_WATER = re.compile(
    r"\bwater\b.{0,48}\b(?:base|foot)\b.{0,28}\b(?:toilet|heater|tank|inodoro)\b|"
    r"\b(?:base|foot)\b.{0,28}\b(?:toilet|heater|tank|inodoro)\b.{0,36}\bwater\b|"
    r"\bagua\b.{0,48}\b(?:base|pie)\b.{0,28}\b(?:inodoro|calentador|tanque)\b",
    re.I,
)
_ODD_SMELL = re.compile(
    r"\b(sometimes|occasional\w*|odd)\b.{0,40}\b(smell\w*|odor\w*|olor)\b|"
    r"\b(smell\w*|odor\w*|olor)\b.{0,32}\b(sometimes|occasional\w*|odd)\b",
    re.I,
)


def _fix_texting(text: str) -> str:
    """Repair tokens that are not words, and the texting word r."""
    parts = text.split()
    fixed: list[str] = []
    for token in parts:
        match = re.match(r"^([^a-z0-9]*)([a-z0-9]+)([^a-z0-9]*)$", token)
        if not match:
            fixed.append(token)
            continue
        prefix, word, suffix = match.group(1), match.group(2), match.group(3)
        if word == "r" and len(parts) >= 3:
            word = "are"
        elif word in _TYPO_TOKEN:
            word = _TYPO_TOKEN[word]
        fixed.append(prefix + word + suffix)
    return " ".join(fixed)


def _gloss(text: str) -> str:
    """Keep the original tokens and add an English gloss beside them."""
    glossed = text
    for pattern, replacement in _GLOSS:
        glossed = pattern.sub(replacement, glossed)
    return glossed


def prepare(text: str) -> str:
    """Fold, fix texting, and gloss Spanish hazard words before the screen."""
    return _gloss(_fix_texting(fold(text)))


def _commercial_without_danger(text: str) -> bool:
    return bool(_COMMERCIAL.search(text)) and not _PRESENT_DANGER.search(text)


def _contained_appliance_water(text: str) -> bool:
    """Water sitting in an appliance basin. Water leaving the appliance is not this."""
    if not _APPLIANCE_BASIN.search(text):
        return False
    if _LEAVING_APPLIANCE.search(text) or _PRESENT_DANGER.search(text) or _sewage_active(text):
        return False
    if not re.search(r"\b(water|standing|sitting|pooled|puddl\w*|wet|agua)\b", text):
        return False
    return bool(
        re.search(r"\b(bottom|tub|basin|sump|reservoir|inside|in the)\b", text)
        or re.search(r"\b(standing|sitting|pooled)\b", text)
    )


def _near(text: str, left: re.Pattern[str], right: re.Pattern[str], window: int) -> bool:
    for match in left.finditer(text):
        if _negated_at(text, match.start()):
            continue
        start = max(0, match.start() - window)
        end = min(len(text), match.end() + window)
        other = right.search(text[start:end])
        if other and not _negated_at(text, start + other.start()):
            return True
    return False


def _compose_water_electric(text: str) -> bool:
    if _contained_appliance_water(text):
        return False
    if not _WATER_MOTION.search(text):
        return False
    if not _ELEC_SURFACE.search(text) and not re.search(r"\bflicker\w*\b", text):
        return False
    flickered = bool(re.search(r"\b(flicker\w*|spark\w*|shock\w*|arcing|shorting)\b", text))
    if flickered and _near(text, _WATER_MOTION, _ELEC_SURFACE, 64):
        return True
    for device in _ELEC_SURFACE.finditer(text):
        if _negated_at(text, device.start()):
            continue
        window = text[max(0, device.start() - 32) : device.end() + 32]
        if _WATER_MOTION.search(window) and _FROM_WORD.search(window):
            return True
    return False


def _steam_product(text: str) -> bool:
    if not re.search(r"\b(steam\s+shower|ducha\s+de\s+vapor|shower\s+valve)\b", text):
        return False
    if not re.search(r"\b(valve|valvula|install\w*|replac\w*|quote|cartridge|handle|service)\b", text):
        return False
    return _STEAM_ESCAPE.search(text) is None and not (_HURT.search(text) and _PERSON.search(text))


def _compose_steam_hurt(text: str) -> bool:
    if _steam_product(text) or _STEAM_ROUTINE.search(text):
        return False
    if _COOKING.search(text) and not re.search(r"\b(heater|boiler|pipe|tank|furnace|water heater)\b", text):
        return False
    if not _STEAM_BOIL.search(text) or not _HURT.search(text):
        return False
    if _PERSON.search(text):
        return True
    return bool(re.search(r"\b(almost|nearly|casi)\b.{0,24}\b(burn\w*|hurt|scald\w*|quem\w*)\b", text))


def _compose_burn_panel(text: str) -> bool:
    if _DUSTY_SEASON.search(text) and not _PANEL_DEVICE.search(text):
        return False
    if _COOKING.search(text) and not _PANEL_DEVICE.search(text):
        return False
    if not _BURN_SMELL.search(text) or not _PANEL_DEVICE.search(text):
        return False
    return _near(text, _BURN_SMELL, _PANEL_DEVICE, 80)


def _compose_gas_symptom(text: str) -> bool:
    if _GAS_BILL.search(text) and not _GAS_SIGNAL.search(text):
        return False
    if not _GAS_WORD.search(text):
        return False
    smell = _GAS_SIGNAL.search(text) or re.search(r"\b(smell\w*|odor\w*|stink\w*|rotten eggs?)\b", text)
    if not smell or _negated_at(text, smell.start()):
        return False
    symptom = _EXPOSURE.search(text)
    return bool(symptom and not _negated_at(text, symptom.start()))


def _compose_co_symptom(text: str) -> bool:
    named = bool(_CO_NAME.search(text))
    if not named:
        return False
    symptom = _EXPOSURE.search(text)
    if not symptom or _negated_at(text, symptom.start()):
        return False
    purchase = re.search(r"\b(install\w*|quote|buy|purchase|price|cost)\b", text)
    event = re.search(
        r"\b(going off|sounding|beeping|beeps|won't stop|wont stop|says|reading|ppm|screaming|sonando|suena|alarm)\b",
        text,
    )
    if purchase and not event:
        return False
    return True


def _compose_definite(text: str) -> tuple[str, str] | None:
    if _commercial_without_danger(text) and not (
        _compose_gas_symptom(text) or _compose_co_symptom(text) or _compose_burn_panel(text) or _compose_steam_hurt(text)
    ):
        if not _compose_water_electric(text):
            return None
    if _compose_water_electric(text):
        return "definite", "Electrical hazard"
    if _compose_steam_hurt(text):
        return "definite", "Active water"
    if _compose_burn_panel(text):
        return "definite", "Electrical hazard"
    if _compose_gas_symptom(text):
        return "definite", "Gas"
    if _compose_co_symptom(text):
        return "definite", "Carbon monoxide"
    return None


def _catalogue_job(text: str) -> bool:
    if not _CATALOGUE.search(text):
        return False
    if _compose_definite(text):
        return False
    if _EXPOSURE.search(text) and _CO_NAME.search(text):
        return False
    if re.search(r"\b(sparks?|sparking|chispas?|smoking|scorch\w*)\b", text):
        return False
    if re.search(r"\bsmoke\b", text) and not re.search(r"\bsmoke\s+(?:alarm|detector)s?\b", text):
        return False
    if _steam_or_scald(text) or _compose_steam_hurt(text):
        return False
    return True


def service_catalogue(text: str) -> bool:
    """An ordinary install, check, or noisy fan. Live hazards are not this."""
    return _catalogue_job(prepare(text))


def _domain_ask(text: str) -> bool:
    """A hazard-domain line that is not a clear routine job and not a clear all-clear."""
    if _PAST_FRAME.search(text) or _HYPOTHETICAL_FRAME.search(text) or _IF_EVER.search(text):
        return False
    if _catalogue_job(text) or _contained_appliance_water(text) or _DUSTY_SEASON.search(text):
        return False
    if _CLEARED.search(text) and not _PRESENT_DANGER.search(text):
        return False
    if _commercial_without_danger(text):
        return False
    if _POPPING.search(text) or _BASE_WATER.search(text) or _ODD_SMELL.search(text):
        return True
    if _PILOT_OUT.search(text) and not (_GAS_SIGNAL.search(text) or re.search(r"\b(rotten eggs?|sulfur|sulphur)\b", text)):
        return True
    return False


def _clauses(text: str) -> list[str]:
    parts = re.split(r"[.;!?]|\bbut\b|\balthough\b|\bpero\b", text)
    return [part.strip() for part in parts if part.strip()]


def _split_turn(text: str) -> list[str]:
    """Clause split, plus a fresh clause at 'and now' so a past visit cannot hide it."""
    marked = re.sub(
        r"\b(and now|but now|and today|and tonight|and this morning|and right now)\b",
        r". \1",
        text,
        flags=re.I,
    )
    return _clauses(marked)


_PRESENT_CUE_WORD = re.compile(
    r"\b(?:right now|just started|this morning|this evening|this afternoon|today|tonight|now|still)\b|"
    r"\b(?:is|are)\s+(?:\w+\s+){0,2}\w+ing\b|"
    r"\b(?:keeps|keep)\s+\w+ing\b|"
        r"\b(?:i|we|it)\s+smells?\b|\bsmells\b|\bsmelling\b|"
        r"\b(?:hissing|sparking|sizzling|crackling|dripping|spraying|pouring|gushing|"
        r"overflowing|charring|slurring)\b|"
        r"\b(?:will not|won't|wont)\b|"
        r"\b(?:is|are)\s+(?:blocked|sounding|going|coming)\b|"
        r"\bthere(?:'s| is| are)\b",
    re.I,
)
_HAZARD_STEM = re.compile(
    r"\b(smoke|smoking|spark\w*|crackle\w*|sizzl\w*|arcing|shock\w*|charr\w*|"
    r"smell\w*|odor\w*|odour\w*|rotten eggs?|sulfur|sulphur|"
    r"dizzy|faint\w*|drows\w*|slurr\w*|confused|collapsed?|vomit\w*|"
    r"burst\w*|sag\w*|flood\w*|overflow\w*|spraying|gushing|pouring|"
    r"alarm|flue|hose|cold to the touch|no heat|eggs?)\b",
    re.I,
)
_PAST_MARK = re.compile(
    r"\b(last year|last winter|last month|last week|last summer|last fall|last autumn|last spring|"
    r"years ago|months ago|a couple of years back|years back|yesterday|"
        r"was serviced|were serviced|had it serviced|was repaired|was fixed|was installed|was hooked up|"
        r"had a leak|had a gas|they repaired|"
    r"you came out|you were here|after the visit|earlier|already gone|gone quiet|has stopped|has reset)\b",
    re.I,
)
_IF_EVER = re.compile(
    r"\b(if i ever|if we ever|if it ever|if you ever|what should i do if|what do i do if|"
    r"if \w+(?:\s+\w+){0,6}\s+ever|hypothetically|what if|household plan|writing a plan)\b",
    re.I,
)
_SOMEONE_ELSE = re.compile(
    r"\b(neighbou?r(?:'s)?|next door|their house|someone else(?:'s)?(?: house)?)\b",
    re.I,
)
_OUR_TOO = re.compile(r"\b(ours|our (?:house|basement|place|side|unit)|we also|us too)\b", re.I)
_CONTEXT_NOUN = re.compile(
    r"\b(furnace|heater|boiler|flue|panel|meter|range|oven|dryer|stove|pipe|ceiling|"
    r"alarm|detector|repair\w*|fixed|leak\w*|gas|line|closet|hose)\b",
    re.I,
)
_HAZARD_NOUN = re.compile(
    r"\b(smell\w*|odor\w*|odour\w*|smoke|spark\w*|crackle\w*|sizzl\w*|shock\w*|"
    r"alarm|dizzy|faint\w*|drows\w*|slurr\w*|vomit\w*|collapsed?|burst\w*|flood\w*|"
    r"flames?|hiss\w*|charr\w*|overflow\w*)\b|"
    r"\bwater\s+(?:is\s+)?(?:moving|running|pouring|coming|spraying)\b",
    re.I,
)
_PLAIN_JOB = re.compile(
    r"\b(sump(?:\s+pump)?|exhaust fan|bath fan|bathroom fan|gfci|gfi|"
    r"flood sensors?|water softener|softener|check-?up|checkup|inspection|"
    r"tune-?up|spigots?|hose bibs?|sillcocks?)\b",
    re.I,
)
_ORDINARY_JOB = re.compile(
    r"\b(drain|clog\w*|spigot|faucet|filter|softener|sump|disposal|sensor)\b",
    re.I,
)
_INSTRUCTION = re.compile(
    r"\b(treat this|treat it as|classify this|classify it as|mark this|mark it as|"
    r"page the on-call|send the on-call)\b",
    re.I,
)


def _present_cue(clause: str) -> bool:
    return bool(_PRESENT_CUE_WORD.search(clause))


_RESOLVED = re.compile(
    r"\b(was repaired|were repaired|they repaired|been quiet|has been quiet|no odor|no smell|not smelling)\b",
    re.I,
)
_STILL_DANGER = re.compile(
    r"\b(i smell|we smell|it smells|smells like|smoke|spark\w*|flames?|spraying|gushing|burst\w*|"
    r"collapsed?|dizzy|vomiting)\b",
    re.I,
)


def _current_danger(clause: str) -> bool:
    """A present-tense hazard. A repaired leak or a what-if plan is not one."""
    if _IF_EVER.search(clause) or _HYPOTHETICAL.search(clause) or _HYPOTHETICAL_FRAME.search(clause):
        return False
    if _RESOLVED.search(clause) and not _hit(clause, _STILL_DANGER):
        return False
    if _present_patterns(clause) is not None:
        return True
    return bool(_present_cue(clause) and (_HAZARD_STEM.search(clause) or _SYMPTOM.search(clause)))


def _clause_away(clause: str) -> bool:
    """A past, hypothetical, or someone-else clause. A present cue in that clause keeps it."""
    someone = bool(_SOMEONE_ELSE.search(clause)) and not _OUR_TOO.search(clause)
    if someone:
        return True
    framed = bool(
        _HISTORICAL.search(clause)
        or _FINISHED.search(clause)
        or _PAST_MARK.search(clause)
        or _HYPOTHETICAL.search(clause)
        or _HYPOTHETICAL_FRAME.search(clause)
        or _IF_EVER.search(clause)
    )
    if not framed:
        return False
    if _current_danger(clause):
        return False
    return True


def _active_context(text: str) -> str | None:
    """Clauses that are happening now. Past clauses only lend an appliance noun."""
    clauses = _split_turn(text) or [text]
    active = [clause for clause in clauses if not _clause_away(clause)]
    if not active:
        return None
    context = " ".join(active)
    if any(_SYMPTOM.search(clause) or _HAZARD_STEM.search(clause) for clause in active):
        extra: list[str] = []
        for clause in clauses:
            if not _clause_away(clause):
                continue
            if _SOMEONE_ELSE.search(clause) and not _OUR_TOO.search(clause):
                continue
            extra.extend(_CONTEXT_NOUN.findall(clause))
        if extra:
            context = context + " " + " ".join(extra)
    return context


def framed_entirely_away(text: str) -> bool:
    """True when every clause is past, hypothetical, or about someone else's house."""
    folded = fold(text)
    return _active_context(folded) is None and bool(
        _HISTORICAL.search(folded)
        or _FINISHED.search(folded)
        or _PAST_MARK.search(folded)
        or _HYPOTHETICAL.search(folded)
        or _HYPOTHETICAL_FRAME.search(folded)
        or _IF_EVER.search(folded)
        or _SOMEONE_ELSE.search(folded)
    )


def mentions_hazard_noun(text: str) -> bool:
    """An unnegated hazard noun in a clause that is happening now.

    A burst, smell, or alarm that lives only in a past or hypothetical clause
    does not open the safety question. The booking request beside it can proceed.
    A catalogue job such as a smoke-alarm replacement does not open it either.
    """
    folded = prepare(text)
    if _catalogue_job(folded):
        return False
    clauses = _split_turn(folded) or [folded]
    live = [clause for clause in clauses if not _clause_away(clause)]
    if not live:
        return False
    return any(
        not _negated_at(clause, match.start())
        for clause in live
        for match in _HAZARD_NOUN.finditer(clause)
    )


def _plain_job(text: str) -> bool:
    return bool(_PLAIN_JOB.search(text) or _PLAIN_FIXTURE.search(text))


def plain_job_text(text: str) -> bool:
    folded = prepare(text)
    if _catalogue_job(folded):
        return _compose_definite(folded) is None
    if not _plain_job(folded):
        return False
    if _present_patterns(folded) is not None:
        return False
    if _fire_or_smoke(folded) or _gas_anywhere(folded) or _SYMPTOM.search(folded):
        return False
    return True


def _scrub_instruction(text: str) -> str:
    scrubbed = _INSTRUCTION.sub(" ", text)
    scrubbed = re.sub(
        r"\bas (?:a |an )?(?:fire|gas|electrical|carbon monoxide)?\s*emergenc\w*\b",
        " ",
        scrubbed,
    )
    scrubbed = re.sub(r"\b(?:fire|gas)\s+emergenc\w*\b", " ", scrubbed)
    scrubbed = re.sub(r"\bemergenc\w*\b", " ", scrubbed)
    scrubbed = re.sub(r"\b(?:page|send)\b.{0,32}\bon-?call\b", " ", scrubbed)
    return scrubbed


def _described_hazard(text: str) -> bool:
    """A real hazard remains after the instruction phrase is removed."""
    scrubbed = _scrub_instruction(text)
    if _present_patterns(scrubbed) is not None:
        return True
    if _fire_or_smoke(scrubbed) or _gas_anywhere(scrubbed):
        return True
    for clause in _split_turn(scrubbed):
        if _gas(clause) or _electrical(clause) or _water(clause):
            return True
    return False


def _instruction_only(text: str) -> bool:
    return bool(_INSTRUCTION.search(text)) and not _described_hazard(text)


def _present_patterns(text: str) -> tuple[str, str] | None:
    """Class patterns for hazards that do not use the textbook noun."""
    if re.search(r"\b(rotten eggs?|sulfur|sulphur|egg smell|smell\w*\s+eggs|"
                 r"smells? like eggs|like eggs|"
                 r"like a leak|smells? like a leak|a leak smells|like gas)\b", text):
        if re.search(r"\b(pilot|burner|oven|range|dryer|furnace|fireplace|meter|cooktop|stove|boiler)\b", text):
            return "definite", "Gas"
    if re.search(r"\bpilot\b", text) and re.search(
        r"\b(keeps dying|keeps going out|goes out|won't stay|wont stay|will not stay)\b",
        text,
    ) and (_ODOR_WORD.search(text) or re.search(r"\b(eggs?|sulfur|sulphur|odor\w*|smell\w*)\b", text)):
        return "definite", "Gas"
    if re.search(r"\b(crackl\w*|sizzl\w*|arcing)\b", text) and re.search(
        r"\b(wall|outlet|switch|panel|box)\b", text
    ):
        return "definite", "Electrical hazard"
    if re.search(r"\bcharr\w*\b", text) and not _COOKING.search(text):
        return "definite", "Electrical hazard"
    if re.search(r"\bshock\w*\b", text) and re.search(r"\b(fixture|railing|rail|outlet|switch|appliance|light)\b", text):
        return "definite", "Electrical hazard"
    if re.search(r"\b(burning[- ]rubber|hot[- ]wire smell|smells like hot wire)\b", text):
        return "definite", "Electrical hazard"
    neuro = re.search(r"\b(drowsy|slurr\w*|confused|out of it|hard to follow|sleepy|woozy)\b", text)
    closed = re.search(r"\b(door shut|door down|doors? closed|closed|shut)\b", text)
    fuel = re.search(r"\b(heater|furnace|boiler|propane|stove|oven|fireplace|generator|engine)\b", text)
    if neuro and closed and fuel:
        return "definite", "Carbon monoxide"
    if (
        re.search(r"\b(blocked|clogged|covered|obstructed)\b", text)
        and re.search(r"\b(exhaust|flue|vent)\b", text)
        and re.search(r"\b(alarm|detector)\b", text)
    ):
        return "definite", "Carbon monoxide"
    if (
        re.search(r"\b(alarm|detector)\b", text)
        and re.search(r"\b(sounding|going off|won't quit|wont quit|will not quit)\b", text)
        and re.search(r"\b(collapsed?|unresponsive|passed out|won't wake|wont wake)\b", text)
    ):
        return "definite", "Carbon monoxide"
    if (
        re.search(r"\b(hose|supply line|water line|line|pipe)\b", text)
        and re.search(r"\b(blew off|let go|burst\w*|split)\b", text)
        and re.search(r"\bwater\b", text)
        and re.search(r"\b(into|through|rooms?|bedrooms?|hall|dining)\b", text)
    ):
        return "definite", "Active water"
    if re.search(r"\boverflow\w*\b", text) and re.search(r"\b(toilet|tub|sink)\b", text) and re.search(
        r"\b(room|ceiling|underneath|below|downstairs)\b", text
    ):
        return "definite", "Active water"
    if re.search(r"\b(swimming pool|lake|river)\b", text) and re.search(r"\bwater\b", text) and re.search(
        r"\b(basement|room|floor)\b", text
    ):
        return "definite", "Active water"
    if re.search(r"\b(infant|baby|newborn|toddler)\b", text) and re.search(
        r"\b(cold to the touch|feels cold|shivering)\b", text
    ):
        return "definite", "Unsafe indoor temperature"
    if re.search(r"\b(pneumonia|on oxygen)\b", text) and (
        _COMFORT.search(text) or re.search(r"\bno heat\b", text)
    ):
        return "definite", "Unsafe indoor temperature"
    foreign = _foreign_hazard(text)
    if foreign is not None:
        return foreign
    if re.search(r"\btingl\w*\b", text) and re.search(
        r"\b(faucet|fixture|appliance|rail(?:ing)?|washer|dryer|switch|outlet|handle|knob|light|tap)\b",
        text,
    ):
        return "definite", "Electrical hazard"
    if _hit(text, re.compile(r"\bsmok(?:e|ing)\b", re.I)) and not re.search(
        r"\bsmoke\s+(?:alarm|detector)s?\b", text
    ) and not _COOKING.search(text):
        return "definite", "Electrical hazard"
    return None


def _foreign_hazard(text: str) -> tuple[str, str] | None:
    """A small lexicon for gas, smoke, fire, shock, and flooding outside English.

    Latin diacritics are already folded off. Arabic-script and Devanagari stay.
    """
    if re.search(r"\bgaz\b", text) and re.search(r"\b(czuj\w*|zapach\w*|smierdz\w*|zawrot\w*|ulatnia\w*)\b", text):
        return "definite", "Gas"
    if re.search(r"گیس", text) and re.search(r"بو", text):
        return "definite", "Gas"
    if re.search(r"\b(pozar|dym|dhua+n|dhuan)\b", text) or re.search(r"دھواں", text):
        return "definite", "Electrical hazard"
    if re.search(r"\baag\b", text) or re.search(r"آگ", text):
        return "definite", "Electrical hazard"
    if re.search(r"\b(kopna\w*|porazen\w*|calambre|jhatk\w*)\b", text) or re.search(r"جھٹک", text):
        return "definite", "Electrical hazard"
    if re.search(r"\bzalan\w*\b", text) or re.search(r"\bpani bhar\b|\bpaani bhar\b", text):
        return "definite", "Active water"
    return None


_STRONG_NOW = re.compile(
    r"\b(won't stop|wont stop|will not stop|pouring|gushing|spraying|spewing|hissing|"
    r"smell|smelling|odor|odour|beeping|sparking|right now|ahora|sin parar)\b",
    re.I,
)
_FINISHED = re.compile(
    r"\b(was repaired|were repaired|got repaired|been repaired|they repaired|"
    r"was resolved|were resolved|been resolved|got resolved|"
    r"was fixed|were fixed|got fixed|been fixed|they fixed|"
    r"has been quiet|been quiet|have not smelled|haven't smelled|not smelled anything|"
    r"nothing is happening)\b",
    re.I,
)
_STILL_GOING = re.compile(
    r"\b(again|still|is leaking|it's leaking|it is leaking|came back|coming back)\b",
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
    """A past or hypothetical clause is skipped. A present-tense cue in it is not."""
    return _clause_away(clause)


def _negated_at(clause: str, index: int) -> bool:
    """True when a negation word governs the token at index, not a hedge or a 'no,' restart."""
    window = clause[max(0, index - 42):index]
    window = re.sub(r"^.*\bno\s*,", "", window)
    window = re.sub(
        r"\bnot\s+(?:urgent|a big deal|that bad|to worry|an emergency)\b",
        " ",
        window,
        flags=re.I,
    )
    if re.search(r"[,;]\s*$", window):
        return False
    words = re.findall(r"[a-z0-9']+", window.lower())
    tail = words[-5:]
    if {"sure", "idea", "certain"} & set(tail):
        return False
    negations = {"no", "not", "without", "sin", "isn't", "isnt", "nothing", "never", "dont", "nahi", "nahin"}
    if any(word in negations for word in tail):
        return True
    after = clause[index : index + 28]
    return bool(re.search(r"\b(nahi|nahin)\b", after, re.I))


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
    if _hit(clause, _GAS_WORD) and (
        _hit(clause, _GAS_SIGNAL) or _hit(clause, re.compile(r"\bgas\s+leak\b|\bleak(?:ing)?\s+gas\b", re.I))
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
    if _CO_BATTERY.search(clause) and (named or chirp):
        if hard:
            return "definite"
        if _CO_PARTS_ERRAND.search(clause) and not _CO_BATTERY_ISSUE.search(clause) and not chirp:
            return None
        return "advice"
    if named and (hard or chirp):
        return "definite"
    exposure = _EXPOSURE.search(clause)
    if named and exposure and not _negated_at(clause, exposure.start()):
        purchase = re.search(r"\b(install\w*|quote|buy|purchase|price|cost)\b", clause)
        event = re.search(
            r"\b(going off|sounding|beeping|beeps|won't stop|wont stop|says|reading|ppm|"
            r"screaming|sonando|suena|alarm|detector)\b",
            clause,
        )
        if not (purchase and not event):
            return "definite"
    if named and re.search(r"\b(install|quote|buy|purchase)\b", clause):
        return None
    return None


def _sewage_active(clause: str) -> bool:
    found = _SEWAGE.search(clause)
    if not found or _negated_at(clause, found.start()):
        return False
    motions = list(_SEWAGE_MOTION.finditer(clause))
    if motions:
        return any(not _negated_at(clause, match.start()) for match in motions)
    if re.search(r"\b(raw sewage|aguas? negras)\b", clause):
        return True
    return bool(re.search(r"\b(drain|toilet|shower|tub|regadera|floor|basement|laundry)\b", clause))


def _water(clause: str, full: str | None = None) -> bool:
    if _sewage_active(clause):
        return True
    blob = full or clause
    if _contained_appliance_water(blob) or _contained_appliance_water(clause):
        return False
    if _commercial_without_danger(blob) and not _PRESENT_DANGER.search(blob):
        return bool(_steam_or_scald(clause))
    foreign = _WATER_I18N.search(clause)
    if foreign and not _negated_at(clause, foreign.start()):
        return True
    path = _WATER_PATH.search(clause)
    if path and not _negated_at(clause, path.start()):
        return True
    if _steam_or_scald(clause):
        return True
    flood = re.search(r"\b(inundand\w*|inundad\w*|inundacion\w*|se inunda)\b", clause)
    if flood and not _negated_at(clause, flood.start()):
        if not re.search(r"\b(inspecc\w*|inspection|cotiz\w*|presupuesto|quote|estimate)\b", clause):
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


_DEVICE = re.compile(
    r"\b(outlet|socket|breaker|wire|wiring|panel|switch|fixture|plug|cord|light)\b",
    re.I,
)
_ELEC_WORD = re.compile(
    r"\b(smoke|smoking|popping|burning|melting|melted|hot|scorch\w*|charred|humo|"
    r"sparks?|sparking|chispas?|arcing)\b",
    re.I,
)
_BARE_SPARK = re.compile(r"\b(sparks?|sparking|chispas?|arcing|electrical fire)\b", re.I)


def _electrical(clause: str) -> bool:
    if _COOKING.search(clause) and not re.search(r"\b(outlet|panel|breaker|wire)\b", clause):
        return False
    if any(not _negated_at(clause, match.start()) for match in _BARE_SPARK.finditer(clause)):
        return True
    for hazard in _ELEC_WORD.finditer(clause):
        if _negated_at(clause, hazard.start()):
            continue
        for device in _DEVICE.finditer(clause):
            if _negated_at(clause, device.start()):
                continue
            if abs(device.start() - hazard.start()) <= 60:
                return True
    if _electrical_damage(clause):
        return True
    return False


_STEAM_ESCAPE = re.compile(
    r"\b(steam|vapor|vapour)\b.{0,40}\b(escap\w*|blast\w*|billow\w*|pour\w*|shoot\w*|"
    r"spew\w*|spurt\w*|jet\w*|uncontrolled|everywhere|scald\w*)\b|"
    r"\b(escap\w*|blast\w*|billow\w*|spew\w*|spurt\w*|jet\w*|scald\w*)\b.{0,40}"
    r"\b(steam|vapor|vapour)\b",
    re.I,
)
_STEAM_ROUTINE = re.compile(r"\b(steam\s+(?:clean\w*|mop|iron|humidifier)|humidifier)\b", re.I)
_SCORCH_WORD = re.compile(
    r"\b(burnt|burned|charred|scorched|blackened|blistered|melting|melted)\b",
    re.I,
)
_BLACK_RING = re.compile(
    r"\bblack\b.{0,32}\b(around|ring|rings|edge|edges|soot|halo|circle)\b|"
    r"\b(around|ring|edges|soot)\b.{0,32}\bblack\b",
    re.I,
)
_ARCING_WORD = re.compile(r"\b(buzz\w*|arcing|flicker\w*|flash(?:es|ed|ing)?)\b", re.I)
_COVER_COLOR = re.compile(r"\b(cover|plate|faceplate)\b", re.I)


def _cover_color_only(text: str) -> bool:
    """A black or white cover plate is a color, not a scorch."""
    if not _COVER_COLOR.search(text):
        return False
    if _SCORCH_WORD.search(text) or _BLACK_RING.search(text) or _ARCING_WORD.search(text):
        return False
    if re.search(r"\b(sparks?|sparking|chispas?|smoke|smoking)\b", text):
        return False
    return bool(re.search(r"\b(black|white|ivory|almond|color|colour|paint)\b", text))


def _dead_or_quote_electrical(text: str) -> bool:
    """A dead outlet or a panel-replacement quote is a job, not a live hazard."""
    if _electrical_damage(text) or re.search(r"\b(sparks?|sparking|chispas?|smoke|smoking)\b", text):
        return False
    dead = bool(re.search(r"\b(dead|no power|without power)\b", text) and _HAZARD_DEVICE.search(text))
    quote = bool(re.search(r"\b(quote|estimate)\b", text) and _HAZARD_DEVICE.search(text))
    return dead or quote


def _steam_or_scald(clause: str) -> bool:
    """Steam or scalding water leaving a pipe or appliance. A steam mop is not this."""
    if _STEAM_ROUTINE.search(clause) or _steam_product(clause):
        return False
    found = _STEAM_ESCAPE.search(clause)
    if found and not _negated_at(clause, found.start()):
        return True
    scald = re.search(r"\bscald\w*\b", clause)
    if scald and not _negated_at(clause, scald.start()) and _WATER_NOUN.search(clause):
        return True
    return False


_HAZARD_DEVICE = re.compile(
    r"\b(outlet|socket|receptacle|breaker|panel|switch|wire|wiring|plug)\b",
    re.I,
)


def _electrical_damage(clause: str) -> bool:
    """A scorched outlet or a buzzing or flashing panel. A dead outlet or a cover color is not."""
    if _COOKING.search(clause) and not re.search(r"\b(outlet|panel|breaker|wire)\b", clause):
        return False
    if not _HAZARD_DEVICE.search(clause):
        return False
    if re.search(r"\bflashlight\b", clause):
        clause = re.sub(r"\bflashlight\b", " ", clause, flags=re.I)
    scorched = _SCORCH_WORD.search(clause) or _BLACK_RING.search(clause)
    arcing = _ARCING_WORD.search(clause)
    if _COVER_COLOR.search(clause) and re.search(r"\b(black|white|ivory|almond|color|colour|paint)\b", clause):
        if not scorched and not arcing:
            return False
    if not scorched and not arcing:
        return False
    if re.search(r"\b(quote|estimate|replacement)\b", clause) and not scorched and not arcing:
        return False
    if re.search(r"\b(dead|no power|without power)\b", clause) and not scorched and not arcing:
        return False
    for device in _HAZARD_DEVICE.finditer(clause):
        if _negated_at(clause, device.start()):
            continue
        for mark in list(_SCORCH_WORD.finditer(clause)) + list(_BLACK_RING.finditer(clause)) + list(_ARCING_WORD.finditer(clause)):
            if _negated_at(clause, mark.start()):
                continue
            if abs(device.start() - mark.start()) <= 80:
                return True
    return False


def _older_adult(clause: str) -> bool:
    for match in _AGE.finditer(clause):
        raw = next((group for group in match.groups() if group), None)
        if raw and int(raw) >= 65:
            return True
    return False


_COMFORT_ALT = re.compile(
    r"\b(heater|furnace|heat|heating|ac|a/c|air|cooling)\b.{0,36}"
    r"\b(not working|stopped|broke|broken|dead|won't come on|wont come on|will not come on|"
    r"won't turn on|wont turn on|will not turn on|isn't heating|isnt heating|isn't cooling|isnt cooling)\b",
    re.I,
)


def _comfort(clause: str, full: str | None = None) -> bool:
    if not (_COMFORT.search(clause) or _COMFORT_ALT.search(clause)):
        return False
    blob = full or clause
    if _VULNERABLE.search(blob) or _FREEZING.search(blob) or _older_adult(blob):
        return True
    if _extreme_temperature(blob):
        return True
    for match in _OVER_UNDER.finditer(blob):
        value = int(match.group(1))
        if match.group(0).lower().startswith(("over", "above")) and value >= 90:
            return True
        if match.group(0).lower().startswith(("under", "below")) and value <= 45:
            return True
    return False


def _emergency_word(clause: str) -> bool:
    if _HYPOTHETICAL.search(clause) and not _GAS_SIGNAL.search(clause) and not _WATER_FORCE.search(clause):
        return False
    if _NOT_EMERGENCY.search(clause):
        return False
    if re.search(r"\b(fee|charge|how much|price|cost|do you do)\b", clause):
        return False
    if re.search(r"\b(emergency plan|safety plan|fire drill|practice drill|household plan)\b", clause):
        return False
    if re.search(r"\bemergency\s+(?:fund|savings|contact|contacts|kit)\b", clause):
        return False
    if re.search(r"\bonly emergency\b", clause):
        return False
    stripped = _FIXTURE.sub(" ", clause)
    found = False
    for match in _EMERGENCY_WORD.finditer(stripped):
        if not _negated_at(stripped, match.start()):
            found = True
    return found


def _happening_now(text: str) -> bool:
    if _STILL_GOING.search(text):
        return True
    return any(not _negated_at(text, match.start()) for match in _STRONG_NOW.finditer(text))


def _past_and_quiet(text: str) -> bool:
    """A finished repair stays routine unless a hazard is happening in this call."""
    if not (_HISTORICAL.search(text) or _FINISHED.search(text)):
        return False
    if _happening_now(text):
        return False
    return True


def _other_hazard(text: str) -> bool:
    for clause in _clauses(text):
        if _skip_clause(clause):
            continue
        if _gas(clause) or _electrical(clause) or _water(clause) or _comfort(clause, text):
            return True
    return False


_WET = re.compile(
    r"\b(water|agua|rain|raining|rainstorm|sprinkler|swimming|soaked|soaking|stream)\b",
    re.I,
)
_PLACE = re.compile(
    r"\b(ceiling|light|hallway|hall|laundry|cabinet|floor|closet|bathroom|kitchen|"
    r"upstairs|bedroom|room|drywall|wall)\b",
    re.I,
)
_FLOW = re.compile(
    r"\b(streaming|stream|spraying|spray|pouring|gushing|soaked|standing water|"
    r"coming down|coming through|running across|running out|shooting|burst|popped|"
    r"let go|water everywhere|will not stop|won't stop|wont stop)\b",
    re.I,
)
_APPLIANCE_LINE = re.compile(
    r"\b(dishwasher|washing machine|washer|ice maker|refrigerator|fridge|supply line|"
    r"hose|water heater|vanity)\b",
    re.I,
)
_SCORCH = re.compile(
    r"\b(scorch\w*|charred|discolored|too hot to touch|burning smell|"
    r"smells like something burning|smell something burning|something burning)\b",
    re.I,
)
_ALARM_UNIT = re.compile(r"\b(alarm|detector|monitor|wall unit)\b", re.I)
_SHRIEK = re.compile(
    r"\b(shrieking|shrieks|screaming|screams|will not stop|won't stop|wont stop|"
    r"will not quit|won't quit|wont quit|keeps sounding|nonstop)\b",
    re.I,
)
_STATUS_OK = re.compile(
    r"\b(no sparks?|nothing is hot|no smoke|green light|light is green|shows green|"
    r"showing green|just want it tested|only want it tested|want it tested|"
    r"only want the annual test|just want a test)\b",
    re.I,
)
_HEDGE = re.compile(
    r"\b(might|maybe|possibly|not sure|cannot tell|can't tell|do not know|don't know|"
    r"a little|slightly|faint|damp spot|wet mark|beeped once)\b",
    re.I,
)


def _building_water(text: str) -> tuple[str, str] | None:
    """Water leaving a ceiling, a wall, or an appliance. A drip into a freezer is not this."""
    if re.search(r"\b(into the freezer|ice bin|ice tray)\b", text):
        return None
    if _contained_appliance_water(text):
        return None
    if _commercial_without_danger(text) and not _PRESENT_DANGER.search(text):
        return None
    indoor = bool(_PLACE.search(text))
    if re.search(r"\b(raining|rainstorm|sprinkler)\b", text) and indoor:
        return "definite", "Active water"
    if re.search(r"\brain\b", text) and re.search(r"\b(indoors|inside|ceiling)\b", text):
        return "definite", "Active water"
    if re.search(r"\bswimming in the\b", text) and indoor:
        return "definite", "Active water"
    if re.search(r"\bwater everywhere\b", text):
        return "definite", "Active water"
    flowing = _FLOW.search(text)
    if flowing and _WET.search(text) and (indoor or _APPLIANCE_LINE.search(text)):
        if _mild_water(text) and not re.search(
            r"\b(streaming|spraying|pouring|gushing|burst|popped|everywhere|standing water|"
            r"won't stop|wont stop|will not stop)\b",
            text,
        ):
            return None
        return "definite", "Active water"
    return None


def _unnamed_alarm(text: str) -> tuple[str, str] | None:
    """A sounding detector or a high reading, even when the caller never says CO."""
    if not _ALARM_UNIT.search(text):
        return None
    if re.search(r"\b(green light|light is green|shows green|showing green)\b", text):
        return None
    if _CO_BATTERY.search(text) and re.search(r"\bchirp", text) and not _SHRIEK.search(text):
        return None
    reading = re.search(r"\b(?:reads?|reading|shows|showing|display(?:ing)?)\s+(\d{2,4})\b", text)
    high = bool(reading and int(reading.group(1)) >= 35)
    sick = bool(_SYMPTOM.search(text))
    if _SHRIEK.search(text) or high or (sick and (_SHRIEK.search(text) or re.search(r"\b(will not|won't|wont)\b", text))):
        return "definite", "Carbon monoxide"
    return None


def _scorch(text: str) -> tuple[str, str] | None:
    if not _SCORCH.search(text):
        return None
    if _COOKING.search(text) and not re.search(r"\b(outlet|panel|breaker|wire|furnace)\b", text):
        return None
    if re.search(r"\b(wall|closet|panel|furnace|heater|dryer|outlet|breaker|drywall)\b", text):
        return "definite", "Electrical hazard"
    return None


def _vulnerable_cold(text: str) -> tuple[str, str] | None:
    person = bool(_VULNERABLE.search(text) or _older_adult(text))
    if not person and not _FREEZING.search(text):
        return None
    if _COMFORT.search(text) or _COMFORT_ALT.search(text) or _extreme_temperature(text) or _FREEZING.search(text):
        if person or _extreme_temperature(text):
            return "definite", "Unsafe indoor temperature"
    return None


def _explicit_clear(text: str) -> bool:
    """A caller who rules the hazard out is not paged for the word they negated."""
    if not _STATUS_OK.search(text):
        return False
    if _other_hazard(text) or _unnamed_alarm(text) or _building_water(text) or _scorch(text):
        return False
    return True


def _soft_electrical(text: str) -> bool:
    if re.search(r"\b(sparks?|smoke|smoking|melting|melted|scorch\w*|charred|burning|too hot|\bhot\b)\b", text):
        return False
    if re.search(r"\b(normal|naturally|expected)\b", text):
        return False
    return bool(re.search(r"\b(slightly warm|a little warm|a bit warm|feels warm|warm to the touch)\b", text))


def _borderline(text: str) -> bool:
    """Uncertain wording asks a safety question instead of booking or paging."""
    if not _HEDGE.search(text):
        return False
    if not re.search(
        r"\b(smell|odor|odour|damp|wet|warm|alarm|detector|outlet|panel|ceiling|furnace|mark|stain|spot|discoloration|vanity)\b",
        text,
    ):
        return False
    if _WATER_FORCE.search(text) or _GAS_WORD.search(text):
        return False
    if re.search(r"\b(sparks?|smoke|screaming|shrieking|hissing|pouring)\b", text):
        return False
    return True


def _class_hazard(text: str) -> tuple[str, str] | None:
    for reader in (_building_water, _unnamed_alarm, _scorch):
        found = reader(text)
        if found is not None:
            return found
    return None


_FLAME = re.compile(r"\b(flames?|on fire|ablaze|catching fire|caught fire)\b", re.I)
_SMOKE_NEAR = re.compile(
    r"\b(filled with smoke|full of smoke|smoke is rolling|smoke rolling|smoke coming|"
    r"smoke pouring|see smoke|seeing smoke)\b|"
    r"\b(smoke|smoking)\b.{0,48}\b(furnace|heater|boiler|dryer|compressor|condenser|"
    r"panel|outlet|stove|oven|water heater|heat pump|closet|unit)\b|"
    r"\b(furnace|heater|boiler|dryer|compressor|condenser|panel|outlet|stove|oven|"
    r"water heater|heat pump|closet)\b.{0,48}\b(smoke|smoking|flames?)\b",
    re.I,
)
_ODOR_WORD = re.compile(
    r"\b(smell\w*|odor\w*|odour\w*|stink\w*|reek\w*|whiff\w*|fumes?)\b",
    re.I,
)
_LEFT_ON = re.compile(
    r"\b(burner|cooktop|stove|range)\b.{0,56}\b(left on|left running|was left|forgot to|"
    r"didn't turn off|did not turn off|won't shut|wont shut|will not shut)\b|"
    r"\b(left on|left running|was left)\b.{0,56}\b(burner|cooktop|stove|range)\b",
    re.I,
)
_FAST_WATER = re.compile(
    r"\b(rising(?:\s+fast)?|sheeting|pushing up|coming up|pouring across|"
    r"running from|will not slow|won't slow|wont slow|faster than)\b",
    re.I,
)
_FLUE = re.compile(r"\b(flue(?: pipe)?|vent pipe|exhaust pipe)\b", re.I)
_FLUE_BAD = re.compile(
    r"\b(loose|disconnected|pulled loose|came off|hanging|separated)\b",
    re.I,
)
_FUEL_BOX = re.compile(r"\b(furnace|boiler|water heater|heater|stove)\b", re.I)
_BROWNED = re.compile(r"\b(brown|browned|blackened|blistered)\b", re.I)
_ELEC_THING = re.compile(r"\b(outlet|receptacle|socket|plug|breaker|panel)\b", re.I)
_TRIP_AGAIN = re.compile(r"\b(keeps opening|trips again|keeps tripping|tripped again)\b", re.I)
_DAMP_MARK = re.compile(
    r"\b(damp|wet|dry)\s+(mark|spot|stain|patch)\b|\b(discoloration|brown spot)\b",
    re.I,
)


def _hit(text: str, pattern: re.Pattern[str]) -> bool:
    return any(not _negated_at(text, match.start()) for match in pattern.finditer(text))


def _fire_or_smoke(text: str) -> bool:
    """Flames or smoke from equipment. A negated cooking mention is not a fire."""
    if _COOKING.search(text) and not re.search(r"\b(outlet|panel|breaker|furnace|dryer|compressor)\b", text):
        return False
    if _hit(text, _FLAME):
        return True
    if _hit(text, _SMOKE_NEAR):
        return True
    burning = re.search(r"\b(burning|blistered|charred)\b", text)
    if burning and not _negated_at(text, burning.start()):
        if re.search(r"\b(closet|furnace|heater|panel|breaker|outlet|dryer|water heater)\b", text):
            if not (_COOKING.search(text) and not re.search(r"\b(outlet|panel|furnace|heater|dryer)\b", text)):
                return True
    return False


def _gas_anywhere(text: str) -> bool:
    """A gas smell pages even when the caller hedges, and not when they say there is none."""
    if re.search(r"\b(car|vehicle|truck|gas station|out of gas|ran out of gas)\b", text):
        return False
    odor_live = _hit(text, _ODOR_WORD)
    gas_live = _hit(text, _GAS_WORD)
    if _GAS_APPLIANCE.search(text) and not odor_live and not re.search(r"\b(leak\w*|hiss\w*)\b", text):
        return False
    if re.search(r"\b(convert|conversion|hook ?up|install)\b", text) and not odor_live:
        return False
    if gas_live and odor_live:
        return True
    rotten = re.search(r"\b(rotten eggs?|sulfur|sulphur)\b", text)
    if rotten and not _negated_at(text, rotten.start()):
        return True
    if _LEFT_ON.search(text) and odor_live:
        return True
    return False


def _fast_water(text: str) -> bool:
    """Water that is rising, sheeting, or coming up. A caller's 'it can wait' does not lower it."""
    if not re.search(r"\b(water|drain|tile|ceiling|sewage)\b", text):
        return False
    if _mild_water(text) and not _FAST_WATER.search(text) and not _WATER_FORCE.search(text):
        return False
    found = _FAST_WATER.search(text)
    if found and not _negated_at(text, found.start()):
        return True
    return False


def _loose_flue(text: str) -> bool:
    flue = _FLUE.search(text)
    if not flue or _negated_at(text, flue.start()):
        return False
    if not _FLUE_BAD.search(text):
        return False
    if re.search(r"\b(dusty|dust)\b", text) and not _FLUE_BAD.search(text):
        return False
    return bool(_FUEL_BOX.search(text) or re.search(r"\bflue\b", text))


def _alarm_with_symptom(text: str) -> bool:
    if not re.search(r"\b(alarm|detector)\b", text):
        return False
    person_sick = re.search(
        r"\b(?:feel|feels|felt|feeling)\s+(?:faint|dizzy|lightheaded|sick|woozy)\b",
        text,
    )
    if not _hit(text, _SYMPTOM) and not (person_sick and not _negated_at(text, person_sick.start())):
        return False
    sounding = re.search(
        r"\b(sounding|going off|won't quit|wont quit|will not quit|won't stop|wont stop|"
        r"will not stop|keeps sounding|nonstop|has been sounding|sonando|suena|sonar|sin parar)\b",
        text,
    )
    if sounding and not _negated_at(text, sounding.start()):
        return True
    return False


def _browned_electrical(text: str) -> bool:
    thing = _ELEC_THING.search(text)
    if not thing:
        return False
    brown = _BROWNED.search(text)
    if brown and not _negated_at(text, brown.start()):
        return True
    trip = _TRIP_AGAIN.search(text)
    hot = re.search(r"\b(smell\w*|hot|scorch\w*|burnt|burned|burning|heat)\b", text)
    if trip and hot and not _negated_at(text, hot.start()) and not _negated_at(text, trip.start()):
        return True
    return False


def _broad_hazard(text: str) -> tuple[str, str] | None:
    """Whole-utterance cues. A hedge or a downplay in the same breath does not clear them."""
    if _fire_or_smoke(text):
        return "definite", "Electrical hazard"
    if _gas_anywhere(text):
        return "definite", "Gas"
    if _loose_flue(text) or _alarm_with_symptom(text):
        return "definite", "Carbon monoxide"
    if _fast_water(text):
        return "definite", "Active water"
    if _browned_electrical(text):
        return "definite", "Electrical hazard"
    return None


def _damp_mark(text: str) -> bool:
    if _WATER_FORCE.search(text) or _FAST_WATER.search(text):
        return False
    return bool(_DAMP_MARK.search(text))


def _lone_category(text: str) -> bool:
    """A bare noun such as 'the water' is a question, not a page."""
    words = re.findall(r"[a-z']+", text)
    fillers = {"the", "a", "an", "my", "our", "just", "only", "some", "it", "its", "is"}
    content = [word for word in words if word not in fillers]
    categories = {"water", "gas", "electric", "electrical", "electricity", "heat", "heater", "alarm"}
    if not content or len(content) > 2:
        return False
    return all(word in categories for word in content)


def _uncertain_without_model(text: str) -> bool:
    """With the embedder down, only an unresolved cue asks. A drain or an address does not."""
    if _routine_context(text) or _explicit_clear(text) or _mild_water(text):
        return False
    return bool(
        re.search(
            r"\b(smell\w*|odor\w*|odour\w*|stink\w*|reek\w*|whiff\w*|fumes?|smoke|flame\w*|"
            r"fire|spark\w*|alarm|detector|dizzy|woozy|headache|nausea|burning|scorch\w*|"
            r"flood\w*|gushing|pouring|sewage|gas)\b",
            text,
        )
    )


_PRESENT_CUE = re.compile(
    r"\b(smells?|smelling|hissing|smoke|smoking|flames?|sparks?|sparking|"
    r"pouring|gushing|spraying|spewing|flooding|again|right now|"
    r"won't stop|wont stop|will not stop|coming in|is leaking|"
    r"dizzy|faint|nause\w*|lightheaded)\b",
    re.I,
)
_PAST_FRAME = re.compile(
    r"\b(?:yesterday|previously|earlier|ago)\b|"
    r"\blast\s+[a-z]+\b|"
    r"\balready\s+(?:fixed|repaired|resolved|serviced|replaced|finished|capped|tagged)\b|"
    r"\b(?:was|were|been|got|had)\s+(?:\w+\s+){0,3}"
    r"(?:fixed|repaired|resolved|serviced|replaced|finished|capped|tagged|quiet)\b",
    re.I,
)
_HYPOTHETICAL_FRAME = re.compile(
    r"\b(what if|hypothetically|suppose|supposing|what would|how much would|"
    r"if we ever|if there were|if it were|someday)\b",
    re.I,
)
_PRICE_FRAME = re.compile(
    r"\b(how much|how many|price|cost|estimate|quot\w*|rate|charge|fee|after[- ]hours)\b",
    re.I,
)
_HABITUAL = re.compile(
    r"\b(each year|every year|every winter|every summer|every fall|every spring|"
    r"whenever we|the first time we)\b",
    re.I,
)
_UNSURE = re.compile(
    r"\b(not sure|don't know|do not know|cannot tell|can't tell|unsure)\b",
    re.I,
)
_YOUNG = re.compile(
    r"\b(baby|babies|infant|newborns?|twins?|triplets?|"
    r"\d+\s*-?\s*(?:day|days|week|weeks)\s*-?\s*old|"
    r"\d+\s*-\s*(?:day|week)-old|(?:day|week|days|weeks)-old)\b|"
    r"\bborn\b.{0,24}\b(?:day|days|week|weeks)\b|"
    r"\b(?:day|days|week|weeks)\b.{0,24}\bborn\b",
    re.I,
)
_COLD_HOME = re.compile(
    r"\b(ice[- ]cold|forties|fifties|shivering|no heat|without heat|"
    r"heat (?:died|is out|won't|wont|will not)|freezing)\b",
    re.I,
)
_GARAGE = re.compile(r"\bgarage\b", re.I)
_MACHINE_RUNNING = re.compile(
    r"\b(car|truck|vehicle|engine|motor|generator|pickup)\b.{0,48}\b(running|idling|left on|is on)\b|"
    r"\b(running|idling|left on|is on)\b.{0,48}\b(car|truck|vehicle|engine|motor|generator|pickup)\b",
    re.I,
)
_GARAGE_SICK = re.compile(
    r"\b(dizzy|faint|lightheaded|sleepy|confused|headache|nause\w*|"
    r"hard to wake|won't wake|wont wake|will not wake|passed out)\b",
    re.I,
)
_STRUCT_DEFORM = re.compile(r"\b(bow\w*|sag\w*|bulg\w*|balloon\w*|swollen|sheeting|tracking)\b", re.I)
_STRUCT_SURFACE = re.compile(r"\b(ceiling|drywall|plaster|stair)\b", re.I)
_DEPTH = re.compile(
    r"\b(?:\d+|one|two|three|four|five|six|several)\s+(?:inch(?:es)?|foot|feet)\s+of\s+water\b",
    re.I,
)
_PLAIN_FIXTURE = re.compile(
    r"\b(spigots?|hose bibs?|bibbs?|sillcocks?|outdoor faucets?|"
    r"water pressure|low pressure|shower pressure)\b",
    re.I,
)
_ROUTINE_SERVICE = re.compile(
    r"\b(no hot water|water heaters?|disposals?|thermostats?|faucets?|"
    r"clog(?:ged)?|puddles?|dripp\w*|spigots?|hose bibs?|sillcocks?|"
    r"water pressure|low pressure|shower pressure)\b",
    re.I,
)


def _present_hazard_cue(text: str) -> bool:
    """A current smell, flow, or symptom. A conditional 'if it were hissing' is not one."""
    scrubbed = re.sub(
        r"\b(?:if|would|were|was)\b.{0,32}\b(?:hissing|smelling|leaking|running)\b",
        " ",
        text,
        flags=re.I,
    )
    return any(not _negated_at(scrubbed, match.start()) for match in _PRESENT_CUE.finditer(scrubbed))


def _young_person(text: str) -> bool:
    return bool(_YOUNG.search(text) or re.search(r"\b(baby|infant|newborn)\b", text))


def _young_cold(text: str) -> bool:
    if not _young_person(text):
        return False
    if _COMFORT.search(text) or _COMFORT_ALT.search(text) or _FREEZING.search(text) or _extreme_temperature(text):
        return True
    return bool(_COLD_HOME.search(text))


def _structural_water(text: str) -> bool:
    """Water that is deforming the building, standing deep, or leaving a split main."""
    if not re.search(r"\bwater\b", text) and not re.search(r"\b(split|burst|throwing)\b", text):
        return False
    if _STRUCT_SURFACE.search(text) and _STRUCT_DEFORM.search(text) and re.search(r"\bwater\b", text):
        return True
    if re.search(r"\bwater\b", text) and re.search(r"\bceiling\b", text) and re.search(r"\bsoft\b", text):
        return True
    if re.search(r"\bwater\b.{0,48}\b(?:down|along)\b.{0,32}\b(?:wall|walls|stair)\b", text):
        return True
    if _DEPTH.search(text) and re.search(
        r"\b(coming|rising|standing|keeps|still|equipment|furnace|heater|mechanical|up to)\b",
        text,
    ):
        return True
    if re.search(r"\b(main|supply)\b", text) and re.search(r"\b(split|burst|ruptur\w*|blew)\b", text):
        if re.search(r"\b(water|throwing|spraying|gushing)\b", text):
            return True
    if re.search(r"\bwater\b.{0,40}\bup to the (?:furnace|heater|panel|equipment)\b", text):
        return True
    return False


def _garage_exhaust(text: str) -> bool:
    if not _GARAGE.search(text) or not _MACHINE_RUNNING.search(text):
        return False
    return bool(_GARAGE_SICK.search(text) or _SYMPTOM.search(text))


def _hiss_odor(text: str) -> bool:
    hiss = re.search(r"\bhiss\w*\b", text)
    if not hiss or _negated_at(text, hiss.start()):
        return False
    if not re.search(r"\b(meter|valve|tank|pipe|line|joint|regulator)\b", text):
        return False
    odor = _ODOR_WORD.search(text) or re.search(r"\b(awful|rotten|terrible)\b", text)
    return bool(odor) and not (odor and _negated_at(text, odor.start()))


def _returned_odor(text: str) -> bool:
    """A present odor after a repair, tag, or shutoff. A price question is not this."""
    if not _hit(text, _ODOR_WORD):
        return False
    if not re.search(r"\b(again|returned|came back|is back|back again|right now)\b", text):
        return False
    return bool(re.search(r"\b(repair\w*|fixed|finished|tagged|utility|meter|line|leak\w*|pipe|valve|shut ?off|capped)\b", text))


def _dry_trap(text: str) -> bool:
    """A drain or septic odor with no backup, overflow, standing water, or symptom."""
    if not re.search(r"\b(drain|sewer|septic|trap)\b", text):
        return False
    if not _ODOR_WORD.search(text):
        return False
    if any(not _negated_at(text, match.start()) for match in _SEWAGE_MOTION.finditer(text)):
        return False
    if re.search(r"\b(overflow\w*|standing|gushing|pouring)\b", text):
        return False
    if _SYMPTOM.search(text):
        return False
    if _WATER_FORCE.search(text):
        return False
    return True


def _plain_fixture(text: str) -> bool:
    if not _PLAIN_FIXTURE.search(text):
        return False
    if _present_hazard_cue(text) or _structural_water(text) or _fire_or_smoke(text):
        return False
    if _SYMPTOM.search(text) or _young_cold(text):
        return False
    return True


def _habitual_mild(text: str) -> bool:
    if not _HABITUAL.search(text):
        return False
    if _GAS_WORD.search(text) or _fire_or_smoke(text) or _structural_water(text):
        return False
    if _WATER_FORCE.search(text) or _SEWAGE.search(text):
        return False
    return True


def _routine_service(text: str) -> bool:
    """A named ordinary job, with no live hazard in the same breath."""
    if _damp_mark(text) or _borderline(text):
        return False
    match = _ROUTINE_SERVICE.search(text)
    if not match or _negated_at(text, match.start()):
        return False
    if _structural_water(text) or _garage_exhaust(text) or _hiss_odor(text) or _returned_odor(text) or _young_cold(text):
        return False
    if _fire_or_smoke(text) or _gas_anywhere(text) or _present_hazard_cue(text):
        return False
    if _SYMPTOM.search(text):
        return False
    return True


def _gas_happening(text: str) -> bool:
    """A gas odor that is being reported now. 'I smelled gas last week' is not."""
    if not _gas_anywhere(text):
        return False
    if re.search(r"\b(smelled|smelt)\b", text) and not _present_hazard_cue(text):
        return False
    return True


def _live_force(text: str) -> bool:
    """Burst or flood inside a price or insurance question is not a live force."""
    if not _WATER_FORCE.search(text):
        return False
    if _commercial_without_danger(text) and not _PRESENT_DANGER.search(text):
        return False
    return True


def _framed_away(text: str) -> tuple[str, str | None] | None:
    """Past, habitual, hypothetical, or price talk is not a page.

    A present hazard cue in the same breath is left for the normal rules.
    If the caller is unsure, ask instead of paging.
    """
    if _habitual_mild(text):
        return "none", None
    live = (
        _structural_water(text)
        or _garage_exhaust(text)
        or _hiss_odor(text)
        or _returned_odor(text)
        or _young_cold(text)
        or _fire_or_smoke(text)
        or _gas_happening(text)
        or (_live_force(text))
        or _sewage_active(text)
        or (_present_hazard_cue(text) and bool(_ELECTRICAL.search(text)))
    )
    if live:
        return None
    hypothetical = bool(_HYPOTHETICAL_FRAME.search(text))
    priced = bool(_PRICE_FRAME.search(text))
    past = bool(_PAST_FRAME.search(text)) and not _present_hazard_cue(text)
    unsure = bool(_UNSURE.search(text))
    if unsure and re.search(r"\b(leak\w*|smell\w*|odor\w*|odour\w*|gas|alarm|smoke|furnace|ceiling|hiss\w*)\b", text):
        return "ask", "Uncertain hazard"
    if not (hypothetical or priced or past):
        return None
    if unsure:
        return "ask", "Uncertain hazard"
    return "none", None


def _situational_hazard(text: str) -> tuple[str, str] | None:
    """Class patterns for hazards that do not use the textbook noun."""
    if _structural_water(text):
        return "definite", "Active water"
    if _garage_exhaust(text):
        return "definite", "Carbon monoxide"
    if _hiss_odor(text) or _returned_odor(text):
        return "definite", "Gas"
    if _young_cold(text):
        return "definite", "Unsafe indoor temperature"
    return None


def classify_emergency(text: str) -> tuple[str, str | None]:
    """Return ('definite'|'ask'|'advice'|'none', label).

    'definite' transfers. 'ask' is the safety question. 'advice' is a chirping
    detector battery. A finished repair stays routine. A negation has to sit
    on the hazard. If the embedder cannot load, an uncertain turn asks rather
    than pretending there is no hazard.
    """
    original = text
    full = prepare(text)
    clauses = _split_turn(full)
    dropped_clause = bool(clauses) and len([clause for clause in clauses if not _clause_away(clause)]) < len(clauses)
    folded = full
    if _instruction_only(folded):
        if _plain_job(folded) or _ORDINARY_JOB.search(folded):
            return "none", None
        return "ask", "Uncertain hazard"
    if _habitual_mild(folded) and _present_patterns(folded) is None and not _fire_or_smoke(folded):
        return "none", None
    active = _active_context(folded)
    if active is None:
        if _UNSURE.search(folded) and re.search(
            r"\b(leak\w*|smell\w*|odor\w*|odour\w*|gas|alarm|smoke|furnace|ceiling|hiss\w*)\b",
            folded,
        ):
            return "ask", "Uncertain hazard"
        return "none", None
    folded = active
    composed = _compose_definite(folded)
    if composed is not None:
        return composed
    if (
        _catalogue_job(folded)
        and not _structural_water(folded)
        and not _fire_or_smoke(folded)
        and not _gas_anywhere(folded)
        and not _SYMPTOM.search(folded)
        and not any(_water(clause, folded) or _gas(clause) or _electrical(clause) for clause in _clauses(folded))
    ):
        return "none", None
    patterned = _present_patterns(folded)
    if patterned is not None:
        return patterned
    if (
        _plain_job(folded)
        and _present_patterns(folded) is None
        and not _water(folded)
        and not _structural_water(folded)
        and not _SYMPTOM.search(folded)
        and not _fire_or_smoke(folded)
        and not _gas_anywhere(folded)
        and not re.search(r"\b(smoke|spark\w*|flame\w*|flooding|burst\w*|tingl\w*|shock\w*)\b", folded)
    ):
        return "none", None
    if _battery_advice(folded) and not _other_hazard(folded):
        return "advice", "CO detector battery"
    advice = False
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
        if _water(clause, folded):
            return "definite", "Active water"
        if _comfort(clause, folded):
            return "definite", "Unsafe indoor temperature"
        if _emergency_word(clause):
            return "definite", "Caller said emergency"
    broad = _broad_hazard(folded)
    if broad is not None:
        return broad
    if advice:
        return "advice", "CO detector battery"
    extra = _class_hazard(folded)
    if extra is not None:
        return extra
    cold = _vulnerable_cold(folded)
    if cold is not None:
        return cold
    situational = _situational_hazard(folded)
    if situational is not None:
        return situational
    if _backup(folded) >= 3:
        return "definite", "Hazard signals"
    if _domain_ask(folded):
        return "ask", "Uncertain hazard"
    if (
        _explicit_clear(folded)
        or _routine_context(folded)
        or _dry_trap(folded)
        or _plain_fixture(folded)
        or _routine_service(folded)
        or _contained_appliance_water(folded)
        or (_commercial_without_danger(folded) and not _gas_anywhere(folded) and not _fire_or_smoke(folded))
    ) and not _soft_electrical(folded) and not _damp_mark(folded):
        return "none", None
    if _mild_water(folded) and not _GAS_SIGNAL.search(folded) and not _CO_HARD.search(folded):
        if not _unnegated(folded, _ELECTRICAL):
            return "none", None
    floor: tuple[str, str | None] = ("none", None)
    if _borderline(folded) or _damp_mark(folded) or _soft_electrical(folded):
        floor = ("ask", "Uncertain hazard")
    if _UNSURE.search(folded) and re.search(
        r"\b(leak\w*|smell\w*|odor\w*|odour\w*|gas|alarm|smoke|furnace|ceiling|hiss\w*)\b",
        folded,
    ):
        floor = ("ask", "Uncertain hazard")
    from app.agent.hazard_nli import nli_opinion
    from app.agent.hazard_semantic import semantic_hazard

    semantic_text = folded if dropped_clause else original
    guessed = semantic_hazard(semantic_text)
    if guessed[1] == "Hazard model unavailable":
        if _uncertain_without_model(folded) or floor[0] == "ask":
            return "ask", "Hazard model unavailable"
        return "none", None
    if _lone_category(folded) and guessed[0] == "definite":
        guessed = ("ask", guessed[1] or "Uncertain hazard")
    if guessed[1] == "Unsafe indoor temperature" and not _comfort_context(folded):
        guessed = ("none", None)
    if guessed[1] == "Active water" and (
        _mild_water(folded) or _contained_appliance_water(folded) or _commercial_without_danger(folded)
    ):
        guessed = ("none", None)
    if guessed[1] == "Electrical hazard" and (_cover_color_only(folded) or _dead_or_quote_electrical(folded)):
        guessed = ("none", None)
    if guessed[0] == "definite" and _catalogue_job(folded):
        guessed = ("none", None)
    if (
        guessed[0] == "definite"
        and _CLEARED.search(folded)
        and not _PRESENT_DANGER.search(folded)
        and _compose_definite(folded) is None
    ):
        guessed = ("none", None)
    if _domain_ask(folded) and guessed[0] == "none":
        guessed = ("ask", "Uncertain hazard")
    if guessed[1] == "Electrical hazard" and _soft_electrical(folded):
        guessed = ("ask", "Electrical hazard")
    if _damp_mark(folded):
        guessed = ("ask", "Uncertain hazard")
    guessed = _stricter(floor, guessed)
    # The zero-shot score only raises an existing safety question to a page.
    # It does not turn a routine clearance into a question or a page.
    if guessed[0] != "ask":
        return guessed
    opinion = nli_opinion(semantic_text)
    if opinion[0] != "definite":
        return guessed
    soft = re.search(
        r"\b(not sure|don't know|do not know|cannot tell|can't tell|unsure|a little|slightly|maybe|possibly|might)\b",
        folded,
    )
    if soft and not _gas_anywhere(folded) and not _situational_hazard(folded):
        return guessed
    if (
        _lone_category(folded)
        or _plain_fixture(folded)
        or _routine_service(folded)
        or _dry_trap(folded)
        or _damp_mark(folded)
        or _soft_electrical(folded)
    ):
        return guessed
    return opinion


def _extreme_temperature(text: str) -> bool:
    for match in list(_DEGREES.finditer(text)) + list(_BARE_TEMP.finditer(text)):
        value = int(match.group(1))
        if value <= 50 or value >= 90:
            return True
    return False


def _mild_water(text: str) -> bool:
    """A drip is not a flood. Semantic water cannot promote it."""
    if _WATER_FORCE.search(text) or _sewage_active(text) or _WATER_PATH.search(text) or _steam_or_scald(text):
        return False
    drip = re.compile(r"\b(drip\w*|leak\w*|weeping|seeping|gote\w*|goutte\w*|tropft|pingando)\b", re.I)
    return _hit(text, drip)


def _comfort_context(text: str) -> bool:
    """No heat or no cooling is urgent only with a vulnerable person or an extreme temperature."""
    if _VULNERABLE.search(text) or _FREEZING.search(text) or _older_adult(text):
        return True
    if _extreme_temperature(text):
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
    if (_HISTORICAL.search(text) or _PAST_MARK.search(text)) and not _present_cue(text) and not _HAZARD_STEM.search(text):
        return True
    if _HYPOTHETICAL.search(text) and not _GAS_SIGNAL.search(text) and not _WATER_FORCE.search(text) and not _ELECTRICAL.search(text):
        return True
    if _sink_backup(text):
        return True
    if _only_negated_gas(text):
        return True
    if _COOKING.search(text) and not re.search(r"\b(outlet|panel|breaker|wire)\b", text) and not _GAS_SIGNAL.search(text):
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
    if re.search(r"\b(fee|charge|how much|price|cost|rate|after[- ]hours|weekend visit)\b", text):
        if (
            not _hit(text, _ODOR_WORD)
            and not _fire_or_smoke(text)
            and not _ELECTRICAL.search(text)
            and not _WATER_FORCE.search(text)
            and not _FAST_WATER.search(text)
        ):
            return True
    if re.search(r"\b(only emergency|wallet|not an emergency)\b", text) and not _GAS_SIGNAL.search(text):
        if not _ELECTRICAL.search(text) and not _WATER_FORCE.search(text) and not _COMFORT.search(text):
            return True
    return False


def _only_negated_gas(text: str) -> bool:
    """'No gas smell' is not a leak. A separate real hazard still stands."""
    if not re.search(r"\b(gas|smell|odor|odour)\b", text):
        return False
    if any(_gas(clause) for clause in _clauses(text) if not _skip_clause(clause)):
        return False
    if _ELECTRICAL.search(text) or _WATER_FORCE.search(text) or _CO_HARD.search(text):
        return False
    return bool(_NEGATED.search(text))


def _sink_backup(text: str) -> bool:
    """A sink or tub that backs up, without sewage or a burst, is a clog."""
    if _WATER_FORCE.search(text) or _sewage_active(text):
        return False
    return bool(re.search(r"\b(sink|tub|bathtub)\b", text) and re.search(r"\bback(?:ing|ed)?\s*up\b", text))


_RANK = {"none": 0, "advice": 1, "ask": 2, "definite": 3}


def _stricter(left: tuple[str, str | None], right: tuple[str, str | None]) -> tuple[str, str | None]:
    if _RANK.get(right[0], 0) > _RANK.get(left[0], 0):
        return right
    return left


def _warm_semantic() -> None:
    """Load the embedder and the NLI model so the first caller turn is not the load."""
    try:
        from app.agent.hazard_semantic import semantic_hazard

        semantic_hazard("warm the multilingual hazard embedder")
    except Exception:
        pass
    try:
        from app.agent.hazard_nli import nli_opinion

        nli_opinion("warm the offline safety classifier")
    except Exception:
        return


_warm_semantic()


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
    if _hit(clause, re.compile(r"\b(gas|propane)\b", re.I)) and _hit(clause, _GAS_SIGNAL):
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
