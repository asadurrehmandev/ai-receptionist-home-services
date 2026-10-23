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
_GAS_APPLIANCE = re.compile(
    r"\bgas\s+(?:water heater|furnace|stove|range|dryer|fireplace|grill)\b|"
    r"\b(?:dryer|grill|range|fireplace)\s+gas\b",
    re.I,
)
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
    r"throwing up|feels? sick|passed out|confused|pounding|migraine|"
    r"maread\w*|mareo|aturdid\w*|desmay\w*|confundid\w*|vomito|tont[oa]s?|tontura)\b|"
    r"\bdolor de cabeza\b|\bduele(?:n)? la cabeza\b|\bdor de cabeca\b|"
    r"\bhead (?:is )?hurts\b|\bhurts? (?:my |the )?head\b",
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
    r"alcantarill\w*|poop water|aguas? negras|"
    r"aguas? sucias?|aguas? podridas?|aguas? sujas?|aguas? podres?|"
    r"maduming tubig|maruming tubig)\b",
    re.I,
)
_SEWAGE_MOTION = re.compile(
    r"\b(backup|backing|backed|coming|overflow|subiendo|regres\w*|devolv\w*|"
    r"subindo|no para|pushing|empuj\w*|saindo)\b",
    re.I,
)
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
    r"heat died|(?:the )?heat (?:just |completely )?(?:quit|died|stopped|failed)|(?:isn't|isnt|not) heating|"
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
    r"bebe|bebé|ancian\w*|abuela|abuelo|niño|nino|niña|nina|nieto|nieta|neto|neta)\b",
    re.I,
)
_FREEZING = re.compile(r"\b(freezing|freeze|shivering|hypotherm\w*|congel\w*)\b", re.I)
_DEGREES = re.compile(
    r"\b(\d{1,3})\s*(?:degrees|degree|grados|graus|°f|°)\b|(\d{1,3})\s*(?:डिग्री|ڈگری|درجة)",
    re.I,
)
_BARE_TEMP = re.compile(
    r"\b(?:it(?:'s| is)|its|inside|indoors)\s+(\d{2,3})\b(?!\s*(?:years?|dollars?|bucks|percent|%))|"
    r"\b(\d{2,3})\s+(?:inside|indoors)\b",
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
    """Lowercase for the rules. Latin accents fold. Other scripts stay intact.

    NFKD on Devanagari and Arabic strips virama and breaks the conjuncts the
    rules match, so only Latin letters are decomposed.
    """
    cleaned = (text or "").replace("’", "'").replace("—", " ").replace("–", " ")
    pieces: list[str] = []
    for char in cleaned:
        code = ord(char)
        latin = code < 0x250 or 0x1E00 <= code <= 0x1EFF
        if latin:
            decomposed = unicodedata.normalize("NFKD", char)
            pieces.append("".join(item for item in decomposed if not unicodedata.combining(item)))
        else:
            pieces.append(char)
    stripped = "".join(pieces).lower()
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return stripped


# Tokens that are not words. Real words such as hose, small, and mouse stay put.
_TYPO_TOKEN = {
    "smel": "smell",
    "smeel": "smell",
    "smke": "smoke",
    "smoek": "smoke",
    "somke": "smoke",
    "smok": "smoke",
    "outlt": "outlet",
    "outet": "outlet",
    "smelg": "smell",
    "hous": "house",
    "watr": "water",
    "wter": "water",
    "watter": "water",
    "runing": "running",
    "extention": "extension",
    "extenion": "extension",
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
    (re.compile(r"\bluces\b"), "luces lights"),
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
_PREVENTION = re.compile(
    r"\b(prevent\w*|insulat\w*|winteriz\w*|before winter|ahead of (?:a |the )?winter|"
    r"so (?:it|they|the pipes|pipes) (?:do not|don't|dont)|"
    r"keep (?:them|it|the pipes|pipes) from)\b",
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
    r"\b(check|service|maintenance|tune|inspect\w*|revision|revisar|mantenimiento|chequeo)\b.{0,48}\b(boiler|caldera)\b|"
    r"\b(caulk\w*|recaulk\w*)\b|"
    r"\b(?:gas\s+)?fireplace\b.{0,48}\b(clean\w*|service|annual|inspect\w*|maintenance|limpieza)\b|"
    r"\b(clean\w*|service|annual|inspect\w*|maintenance|limpieza)\b.{0,48}\b(?:gas\s+)?fireplace\b|"
    r"\b(shower\s*heads?|showerhead|regadera|cabezal de la ducha)\b|"
    r"\b(dryer|secadora)\b.{0,40}\b(gas\s+(?:line|connection)|linea de gas)\b|"
    r"\b(gas\s+(?:line|connection)|linea de gas)\b.{0,40}\b(dryer|secadora|grill|parrilla)\b|"
    r"\b(grill|parrilla|barbecue|bbq)\b.{0,32}\b(gas\s+line|linea de gas)\b|"
    r"\bflood\s+lights?\b|"
    r"\bsparkling\s+water\b",
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
    r"\b(fixtures?|outlets?|sockets?|receptacles?|wiring|electric\w*|lights?|lamps?|luminaires?|cords?|breakers?|panels?)\b",
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


def _prevention_without_danger(text: str) -> bool:
    """Insulating so a pipe does not burst is not a burst that is happening."""
    return bool(_PREVENTION.search(text)) and not _PRESENT_DANGER.search(text)


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
    touching = bool(re.search(r"\b(onto|into|against|touching|on top of|landing on)\b", text))
    if touching and _near(text, _WATER_MOTION, _ELEC_SURFACE, 64):
        return True
    if re.search(r"\blanding on\b", text) and _WATER_MOTION.search(text) and _ELEC_SURFACE.search(text):
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


def _water_on_power(text: str) -> bool:
    """Water touching a light, outlet, cord, or panel. A dry flood-light install is not this."""
    if re.search(r"\bsparkling\s+water\b", text):
        return False
    if _contained_appliance_water(text):
        return False
    if re.search(r"\bflood\s+lights?\b", text) and not _WATER_MOTION.search(text):
        return False
    if _compose_water_electric(text):
        return True
    if not _WATER_MOTION.search(text):
        return False
    if re.search(r"\b(?:no water|without water|not wet|sin agua)\b", text):
        return False
    return _near(text, _WATER_MOTION, _ELEC_SURFACE, 96)


def _catalogue_job(text: str) -> bool:
    if not _CATALOGUE.search(text):
        return False
    if _water_on_power(text) or _smoke_happening(text):
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
    r"\b(smoke|smoking|sparks?|sparking|crackle\w*|sizzl\w*|arcing|shock\w*|charr\w*|"
    r"smell\w*|odor\w*|odour\w*|rotten eggs?|sulfur|sulphur|"
    r"dizzy|faint\w*|drows\w*|slurr\w*|confused|collapsed?|vomit\w*|"
    r"burst\w*|sag\w*|flood(?:ing|ed|s)?(?!\s+lights?)|overflow\w*|spraying|gushing|pouring|"
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
    r"\b(smell\w*|odor\w*|odour\w*|smoke|sparks?|sparking|crackle\w*|sizzl\w*|shock\w*|"
    r"alarm|dizzy|faint\w*|drows\w*|slurr\w*|vomit\w*|collapsed?|burst\w*|"
    r"flood(?:ing|ed|s)?(?!\s+lights?)|"
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
    r"\b(?:treat this|treat it as|treat the call|classify this|classify it|"
    r"mark this|mark it as|page the on-call|send the on-call|page (?:this|it) as|"
    r"role-?play|pretend (?:this|that|it|the|there)|act as if|you are now|"
    r"you are the (?:on-?call|dispatcher|receptionist|agent|system|desk)|"
    r"ignore (?:all |any |the )?(?:previous|prior|above|your|script|instructions)|"
    r"disregard (?:all |any )?(?:previous|prior|above)|"
    r"override (?:your|the) instructions|"
    r"clasifica(?:r| esto| esta)|ignora las instrucciones|"
    r"system\s*:|escalate (?:this|the) (?:call|visit)|priority override|"
    r"this (?:call|one|visit) is (?:an? )?(?:[\w]+\s+){0,3}emergenc|"
    r"say (?:that )?there(?:'s| is) (?:a |an )?(?:fire|gas|emergency)|"
    r"tell (?:them|him|her|the desk|everyone) (?:it(?:'s| is)|there(?:'s| is)|that it(?:'s| is)) (?:a |an )?(?:fire|gas|emergency))\b",
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
    context = ". ".join(active)
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
    if _catalogue_job(folded) or _prevention_without_danger(folded):
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


def _scrub_emergency_word(text: str) -> str:
    return re.sub(r"\bemergenc\w*\b", " ", text or "", flags=re.I)


def _booking_sentence(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:book|schedule|appointment|quote|install|estimate|tune-?up|visit)\b",
            text or "",
            re.I,
        )
    )


def _without_roleplay(text: str) -> str:
    """Drop a sentence that only names an emergency class.

    A later sentence that states smoke, gas, or water stays. Fire words that
    live only inside the instruction sentence do not. A booking that was
    hiding inside the instruction sentence stays, without the class name.
    """
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    kept: list[str] = []
    for part in parts:
        piece = part.strip()
        if not piece:
            continue
        if not _INSTRUCTION.search(piece):
            kept.append(piece)
            continue
        scrubbed = _scrub_instruction(piece)
        scrubbed = re.sub(r"\b(?:on fire|fire|flames?|ablaze)\b", " ", scrubbed, flags=re.I)
        if _live_physical(scrubbed):
            kept.append(scrubbed)
            continue
        remainder = _scrub_emergency_word(scrubbed)
        if _booking_sentence(remainder) or _plain_job(remainder) or _ordinary_fixture(remainder):
            kept.append(remainder)
    return " ".join(kept).strip()


def _without_bare_booking(text: str) -> str:
    """Remove the word emergency from a booking sentence that has no live hazard.

    The job description stays. A second sentence that states smoke or water stays whole.
    """
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    kept: list[str] = []
    for part in parts:
        piece = part.strip()
        if not piece:
            continue
        if _booking_sentence(piece) and not _live_physical(_scrub_emergency_word(piece)):
            kept.append(_scrub_emergency_word(piece))
            continue
        kept.append(piece)
    return " ".join(kept).strip()


_LET_GO = re.compile(
    r"\b(?:let go|gave way|gave out|came apart|blew apart|blew off)\b",
    re.I,
)
_SUPPLY_NOUN = re.compile(
    r"\b(?:supply|hose|line|pipe|bib|main|washer|laundry)\b",
    re.I,
)
_FILLING = re.compile(
    r"\b(?:filling up|filling with water|is filling|are filling|keeps filling|puno)\b|"
    r"\bfilling\b",
    re.I,
)
_FILL_PLACE = re.compile(
    r"\b(?:rooms?|basement|house|garage|laundry|kitchen|mudroom|hall|kusina)\b",
    re.I,
)
_DETECTOR_DEVICE = re.compile(r"\b(?:detectors?|alarms?|alarme|alarma)\b", re.I)
_DETECTOR_HOWL = re.compile(
    r"\b(?:howling|screaming|shrieking|blaring|wailing|aullando|gritando|uivando|baj raha)\b|"
    r"\b(?:won't|wont|will not|cannot|can't)\s+quit\b",
    re.I,
)
# A howling person is not a detector. A unit, a ceiling, or an alarm is.
_HOWL_SOURCE = re.compile(
    r"\b(?:detectors?|alarms?|alarme|alarma|units?|devices?|apparatus|aparatos?|"
    r"something|ceiling|wall|techo|caja|unidad|unidades|sensors?)\b",
    re.I,
)
_ILLNESS = re.compile(
    r"\b(?:dizzy|dizziness|nauseous|nauseated|nausea|vomit\w*|headaches?|pounding|"
    r"faint|feels? sick|sick|mareo|mareada|chakkar|nahihilo|tont[oa]s?|tontura)\b|"
    r"\bdolor de cabeza\b|\bduele(?:n)? la cabeza\b|\bdor de cabeca\b",
    re.I,
)


def _uncontrolled_water_now(text: str) -> bool:
    """A supply that has let go, or a room that is filling, in this clause."""
    if not (text or "").strip():
        return False
    if re.search(r"\bfilling the (?:tub|bath|pool)\b", text, re.I):
        return False
    let_go = bool(_LET_GO.search(text) and _SUPPLY_NOUN.search(text))
    filling = bool(_FILLING.search(text) and (_FILL_PLACE.search(text) or re.search(r"\bwater\b", text, re.I)))
    return let_go or filling


def _uncontrolled_water(text: str) -> bool:
    """Present uncontrolled water. A past 'let go' does not count."""
    clauses = _split_turn(text) or [text]
    return any(
        _uncontrolled_water_now(clause)
        for clause in clauses
        if clause and not _clause_away(clause)
    )


def _sounding_detector(text: str) -> bool:
    """A howling unit plus illness. The caller does not have to say detector.

    A chirp, a battery with nobody sick, and a person who is screaming are not this.
    A drip in the same sentence does not cancel it.
    """
    if not (text or "").strip():
        return False
    if _intermittent_chirp(text):
        return False
    if re.search(r"\bchirp", text, re.I) and not _DETECTOR_HOWL.search(text):
        return False
    if not _DETECTOR_HOWL.search(text):
        return False
    ill = bool(_symptom_live(text) or _ILLNESS.search(text))
    if not ill:
        return False
    if re.search(r"\b(?:battery|batteries)\b", text, re.I) and not ill:
        return False
    return bool(_DETECTOR_DEVICE.search(text) or _HOWL_SOURCE.search(text))


def _live_physical(text: str) -> bool:
    """A hazard that is happening in this text, after roleplay lines are gone.

    A running toilet or a mild drip is a job. Water on a light, a supply that
    let go, a room that is filling, a howling detector, and live smoke are not,
    even when the same sentence names a catalogue fixture.
    """
    if not (text or "").strip():
        return False
    if _uncontrolled_water_now(text) or _sounding_detector(text):
        return True
    if _ordinary_fixture(text) and not _water_on_power(text) and not _smoke_happening(text):
        if not _gas_happening(text) and not _fire_or_smoke(text) and not _sewage_active(text):
            return False
    if _water_on_power(text) or _smoke_happening(text):
        return True
    if _gas_happening(text) or _fire_or_smoke(text):
        return True
    if _sewage_active(text) or _co_alarm_and_symptom(text) or _comfort_bundle(text):
        return True
    if _structural_water(text):
        return True
    if _mild_water(text):
        return False
    if _compose_definite(text) is not None or _present_patterns(text) is not None:
        return True
    return False


def _present_hazard_clause(text: str) -> bool:
    """True when a hazard is happening, including water on a light or live smoke.

    An instruction that only names a class is not a clause. A past or
    hypothetical clause is not one either. Catalogue words and a street
    shape do not erase a clause that is happening now.
    """
    screened = _without_roleplay(text)
    active = _active_context(screened)
    if active is None:
        return False
    return _live_physical(active)


def _described_hazard(text: str) -> bool:
    """A present physical hazard remains after the instruction phrase is removed.

    Naming an emergency class, or a routine drip beside that name, is not one.
    """
    return _present_hazard_clause(text)


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
    if re.search(r"گیس", text) and re.search(r"بو", text) and not re.search(r"نہیں", text):
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
    negations = {"no", "not", "without", "sin", "isn't", "isnt", "nothing", "never", "dont", "nahi", "nahin", "walang"}
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
    if foreign:
        odor_at = foreign.start()
        odor_word = re.search(
            r"\b(?:odeur|cheiro|cheira|mui|amoy|olor|huele|fuite|vazamento|leak|smell)\b",
            foreign.group(0),
        )
        if odor_word:
            odor_at = foreign.start() + odor_word.start()
        before_odor = clause[max(0, odor_at - 14) : odor_at]
        if re.search(r"\b(?:sem|sin|no|not|without|walang)\b", before_odor):
            foreign = None
        elif not _negated_at(clause, odor_at):
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


def _symptom_live(text: str) -> bool:
    """A bodily symptom that is not negated in the few words before it."""
    match = _SYMPTOM.search(text) or _EXPOSURE.search(text)
    if not match or _negated_at(text, match.start()):
        return False
    window = text[max(0, match.start() - 32) : match.start()]
    if re.search(r"\b(no|not|n't|without|nobody|no one|sin|nunca|walang)\b", window, re.I):
        return False
    return True


def _intermittent_chirp(text: str) -> bool:
    """A few chirps, not an alarm that keeps going, and nobody is sick."""
    if not re.search(r"\bchirp", text):
        return False
    if not re.search(r"\b(carbon monoxide|monoxide|monoxido|\bco\b|detector|alarm)\b", text):
        return False
    if re.search(r"\b(keeps|kept|won't stop|wont stop|will not stop|nonstop|continu)\b", text):
        return False
    if _symptom_live(text):
        return False
    return True


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
        if hard or _symptom_live(clause):
            return "definite"
        if _CO_PARTS_ERRAND.search(clause) and not _CO_BATTERY_ISSUE.search(clause) and not chirp:
            return None
        return "advice"
    if chirp and named:
        # A continuous chirp is an alarm. A few chirps are a battery.
        if _symptom_live(clause) or re.search(
            r"\b(keeps|kept|won't stop|wont stop|will not stop|nonstop|continu)\b",
            clause,
        ):
            return "definite"
        return "advice"
    if named and hard:
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
    """Sewage that is moving. Textbook nouns and everyday dirty-water wording both count."""
    if re.search(r"गंदा पानी|गन्दा पानी", clause) and re.search(r"आ रहा|ऊपर|वापस|नाली", clause):
        return True
    if re.search(r"گندا پانی", clause) and re.search(r"آ رہا|اوپر|واپس|نالے|نالی", clause):
        return True
    if re.search(r"مياه الصرف|مياه المجاري", clause) and not re.search(r"لا توجد|بدون", clause):
        return True
    if re.search(r"بالوعة", clause) and re.search(r"مياه|مجاري|صرف", clause) and not re.search(r"لا توجد|بدون", clause):
        return True
    if re.search(r"\b(?:maruming|maduming) tubig\b", clause, re.I) and re.search(
        r"\b(?:umaakyat|umakyat|kanal|banyo|sahig|lababo)\b", clause, re.I
    ):
        return True
    if re.search(r"\bganda\b", clause, re.I) and re.search(r"\b(?:pani|paani)\b", clause, re.I) and re.search(
        r"\b(?:upar|aa raha|aa rahi|nali|naale|naali)\b", clause, re.I
    ):
        return True
    if re.search(r"\besgoto\b", clause, re.I) and re.search(
        r"\b(?:voltando|subindo|saindo|transbord\w*|devolv\w*)\b", clause, re.I
    ):
        return True
    if re.search(r"\bagua\s+(?:suja|podre|sucia|podrida)\b", clause, re.I) and re.search(
        r"\b(?:ralo|desague|coladera|drenaje|devolv\w*|subindo|subiendo|saindo|no para)\b",
        clause,
        re.I,
    ):
        return True
    found = _SEWAGE.search(clause)
    if not found or _negated_at(clause, found.start()):
        return False
    motions = list(_SEWAGE_MOTION.finditer(clause))
    if motions:
        return any(not _negated_at(clause, match.start()) for match in motions)
    if re.search(r"\b(raw sewage|aguas? negras|aguas? sucias?|aguas? podridas?|aguas? sujas?|aguas? podres?)\b", clause):
        return True
    return bool(
        re.search(
            r"\b(drain|toilet|shower|tub|regadera|floor|basement|laundry|"
            r"desague|coladera|drenaje|ralo|lavabo|lababo|bano)\b",
            clause,
        )
    )


def _water(clause: str, full: str | None = None) -> bool:
    if _sewage_active(clause):
        return True
    blob = full or clause
    if _contained_appliance_water(blob) or _contained_appliance_water(clause):
        return False
    if _commercial_without_danger(blob) and not _PRESENT_DANGER.search(blob):
        return bool(_steam_or_scald(clause))
    if _prevention_without_danger(blob) or _prevention_without_danger(clause):
        return False
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
    blob = full or clause
    if _comfort_bundle(blob):
        return True
    if not (_COMFORT.search(clause) or _COMFORT_ALT.search(clause) or _LOSS_I18N.search(blob)):
        return False
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
    if _prevention_without_danger(text):
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


def _smoke_happening(text: str) -> bool:
    """Smoke or flames that are happening. A smoke-alarm install or a negated smoke is not."""
    if re.search(r"\b(?:no smoke|without smoke|sin humo|walang usok|not smoking)\b", text):
        if not re.search(r"\b(?:smoke|smoking)\b.{0,48}\b(?:coming|pouring|from|rolling|see)\b", text):
            return False
    if _fire_or_smoke(text):
        return True
    stripped = re.sub(r"\bsmoke\s+(?:alarm|detector)s?\b", " ", text, flags=re.I)
    if re.search(r"\b(?:chirp\w*|beeping|battery|install\w*|replac\w*|swap|quote)\b", text) and not re.search(
        r"\b(?:smoke|smoking|humo|usok|dhuan|dhuaan|fuma[cç]a)\b",
        stripped,
    ):
        return False
    return _hit(stripped, re.compile(r"\b(?:smoke|smoking|humo|usok|dhuan|dhuaan|fuma[cç]a)\b", re.I))


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


def _hedged_alternative(text: str) -> bool:
    """'Possibly a gas smell, or maybe it is just the trash' is a question."""
    if _symptom_live(text) or _fire_or_smoke(text) or _live_force(text):
        return False
    if not re.search(r"\b(?:possibly|maybe|might)\b", text):
        return False
    if not re.search(r"\b(?:smell\w*|odor\w*|odour\w*|gas)\b", text):
        return False
    return bool(re.search(r"\b(?:or maybe|just the trash|just trash|or perhaps)\b", text))


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
    if (_commercial_without_danger(text) or _prevention_without_danger(text)) and not _PRESENT_DANGER.search(text):
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


def rules_screen(text: str) -> tuple[str, str | None]:
    """Hand rules. 'definite' transfers. 'ask' is the safety question.

    'advice' is a chirping detector battery. A finished repair stays routine.
    A negation has to sit on the hazard. If the embedder cannot load, an
    uncertain turn asks rather than pretending there is no hazard.
    """
    original = text
    full = prepare(text)
    screened = _without_bare_booking(_without_roleplay(full))
    if _instruction_only(full):
        if (
            _plain_job(full)
            or _ORDINARY_JOB.search(full)
            or _ordinary_fixture(full)
            or (
                screened
                and (
                    _ordinary_fixture(screened)
                    or _plain_job(screened)
                    or _booking_sentence(screened)
                    or _ORDINARY_JOB.search(screened)
                    or re.search(
                        r"\b(?:toilet|faucet|aerator|vanity|handle|spout|furnace|heater|disposal)\b",
                        screened,
                    )
                )
            )
        ):
            return "none", None
        return "ask", "Uncertain hazard"
    if screened:
        full = screened
    clauses = _split_turn(full)
    dropped_clause = bool(clauses) and len([clause for clause in clauses if not _clause_away(clause)]) < len(clauses)
    folded = full
    # A booking, a slot, or a routine drip has no present hazard clause.
    # Skipping the semantic model here saves the turn budget. The learned
    # head still embeds this turn in classify_emergency.
    if _fast_routine(folded):
        return "none", None
    if _intermittent_chirp(folded) and not _other_hazard(folded):
        return "advice", "CO detector battery"
    if _habitual_mild(folded) and _present_patterns(folded) is None and not _fire_or_smoke(folded):
        return "none", None
    if _hedged_alternative(folded):
        return "ask", "Uncertain hazard"
    active = _active_context(folded)
    if active is None:
        if _UNSURE.search(folded) and re.search(
            r"\b(leak\w*|smell\w*|odor\w*|odour\w*|gas|alarm|smoke|furnace|ceiling|hiss\w*)\b",
            folded,
        ):
            return "ask", "Uncertain hazard"
        return "none", None
    folded = active
    if _uncontrolled_water_now(folded):
        return "definite", "Active water"
    if _sounding_detector(folded):
        return "definite", "Carbon monoxide"
    if _sewage_active(folded):
        # The spoken line comes from the source. This label stays "Active water"
        # so an older sewer-water case keeps its recorded class.
        return "definite", "Active water"
    composed = _compose_definite(folded)
    if composed is not None:
        return composed
    if _water_on_power(folded) and not _mild_water(folded):
        return "definite", "Electrical hazard"
    if _smoke_happening(folded):
        return "definite", "Electrical hazard"
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
        # The word emergency, by itself, is not a present hazard.
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
    if _drip_near_power(folded):
        return "ask", "Uncertain hazard"
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


def _temp_reading(match: re.Match[str]) -> int | None:
    raw = next((group for group in match.groups() if group and group.isdigit()), None)
    if raw is None:
        return None
    return int(raw)


def _extreme_temperature(text: str) -> bool:
    for match in list(_DEGREES.finditer(text)) + list(_BARE_TEMP.finditer(text)):
        value = _temp_reading(match)
        if value is None:
            continue
        if value <= 50 or value >= 90:
            return True
    return False


def _drip_near_power(text: str) -> bool:
    """A drip headed toward power is a question, not a booking and not a page."""
    if not re.search(r"\b(drip\w*|leak\w*|weeping|seeping)\b", text):
        return False
    if not re.search(r"\b(breaker|panel|outlet|socket|electrical)\b", text):
        return False
    if _PRESENT_DANGER.search(text) or re.search(r"\b(sparks?|sparking|smoke|smoking)\b", text):
        return False
    return True


def _mild_water(text: str) -> bool:
    """A drip is not a flood. Semantic water cannot promote it.

    A supply that let go, or a room that is filling, is not a mild drip
    even when the same sentence also says drip.
    """
    if _uncontrolled_water(text) or _sounding_detector(text):
        return False
    if _WATER_FORCE.search(text) or _sewage_active(text) or _WATER_PATH.search(text) or _steam_or_scald(text):
        return False
    drip = re.compile(r"\b(drip\w*|leak\w*|weeping|seeping|gote\w*|goutte\w*|tropft|pinga\w*)\b", re.I)
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


_LOSS_I18N = re.compile(
    r"nao tem aquecimento|sem aquecimento|sem ar condicionado|"
    r"aquecedor parou|aquecedor quebrou|aquecedor nao liga|aquecedor nao funciona|"
    r"nao liga o aquecedor|"
    r"walang init|walang aircon|"
    r"heater band|ac band|garmi nahi|thandak nahi|"
    r"हीटर बंद|एसी बंद|"
    r"ہیٹر بند|اے سی بند|ای سی بند|"
    r"no hay calef|sin calor|sin aire",
    re.I,
)
_PERSON_I18N = re.compile(
    r"\b(dadi|dada|baccha|bachcha|buzurg|lola|lolo|sanggol|avo|avos|bebe|idoso|idosa|nieto|nieta)\b|"
    r"दादी|दादा|बच्चा|बुजुर्ग|"
    r"دادی|دادا|بچہ|"
    r"جدتي|جدي|رضيع|مسن",
    re.I,
)
_EXTREME_WORD = re.compile(
    r"bahut thand|bohot thand|bahut garmi|bohot garmi|"
    r"muito frio|muito calor|gelad[ao]s?|"
    r"sobrang lamig|sobrang init|"
    r"बहुत ठंड|बहुत गर्मी|"
    r"بہت ٹھنڈ|بہت گرمی|"
    r"البرد شديد|الحر شديد|برد شديد|حر شديد",
    re.I,
)
_FLICKER_APPLIANCE = re.compile(r"\b(toaster|microwave|oven|dryer|dishwasher)\b", re.I)


def _comfort_bundle(text: str) -> bool:
    """No heat or no cooling, plus a vulnerable person, plus an extreme temperature."""
    loss = bool(_COMFORT.search(text) or _COMFORT_ALT.search(text) or _LOSS_I18N.search(text))
    if not loss and re.search(r"تدفئة|تبريد", text) and "لا" in text:
        loss = True
    if not loss:
        return False
    person = bool(_VULNERABLE.search(text) or _older_adult(text) or _PERSON_I18N.search(text))
    if not person:
        return False
    return bool(_extreme_temperature(text) or _EXTREME_WORD.search(text) or _FREEZING.search(text))


def _co_alarm_and_symptom(text: str) -> bool:
    """An active monoxide alarm plus a bodily symptom pages. A chirp does not."""
    symptom = _symptom_live(text) or bool(re.search(r"\b(?:tonto|tontura|dor de cabeca)\b", text))
    if not symptom:
        return False
    if _intermittent_chirp(text):
        return False
    named = bool(re.search(r"\b(?:carbon monoxide|monoxide|monoxido|\bco\b)\b", text))
    device = bool(re.search(r"\b(?:alarms?|alarme|detector|alert|alarma)\b", text))
    return named and device


def _noun_active_ask(text: str) -> bool:
    """A hazard noun with a present-tense or symptom cue is at least a question."""
    active = _active_context(text)
    if not active:
        return False
    if _catalogue_job(active) or _plain_job(active) or _GAS_BILL.search(active):
        return False
    noun = re.search(r"\b(gas|propane|monoxide|monoxido|smoke|spark\w*|sewage|flood\w*)\b", active)
    if not noun or _negated_at(active, noun.start()):
        return False
    cue = re.search(
        r"\b(smell\w*|odor\w*|odour\w*|hiss\w*|leak\w*|pour\w*|gush\w*|sounding|going off|headache|dizzy|nausea)\b",
        active,
    )
    if not cue or _negated_at(active, cue.start()):
        return False
    return True


def _appliance_flicker(text: str) -> bool:
    """Flicker while an appliance runs is a question. A lamp that only flickers is not."""
    if not re.search(r"\bflicker", text):
        return False
    if re.search(r"\b(no smoke|no sparks|without sparks|without smoke)\b", text):
        return False
    if re.search(r"\b(sparks?|sparking|smoke|smoking)\b", text):
        return False
    return bool(_FLICKER_APPLIANCE.search(text))


def _stem_negated(text: str, index: int) -> bool:
    """A nearby nahi/no cancels a stem. 'ruk nahi' and 'band nahi' mean it will not stop."""
    snippet = text[index : index + 24]
    if re.search(r"\b(?:band|ruk)\s+(?:nahi|nahin)\b", snippet):
        return False
    if re.search(r"\b(?:nahi|nahin|walang)\b", snippet):
        return True
    before = text[max(0, index - 18) : index]
    return bool(re.search(r"\b(?:no|not|without|nahi|nahin|walang)\b", before))


def _multilingual_compose(text: str) -> tuple[str, str] | None:
    """Page a live hazard from the words that carry it, in any supported language.

    Romanized Urdu and Hindi use odor, burst, and spark stems. A negation
    beside that stem (koi boo nahi, chingari nahi) is not a live hazard.
    """
    odor = re.search(r"\b(?:boo+|badbu+|gandh)\b", text)
    if re.search(r"\bgas\b", text) and odor and not _stem_negated(text, odor.start()):
        return "definite", "Gas"
    if re.search(r"\b(?:ande|anda|anday)\b", text) and re.search(r"\bboo+\b", text):
        egg = re.search(r"\bboo+\b", text)
        if egg and not _stem_negated(text, egg.start()):
            return "definite", "Gas"
    burst = re.search(r"\b(?:phat\w*|toot\w*)\b", text)
    if burst and not _stem_negated(text, burst.start()) and re.search(r"\b(?:pani|paani|pipe|nalka)\b", text):
        return "definite", "Active water"
    spark = re.search(r"\b(?:chingari\w*|sharar\w*)\b", text)
    device = re.search(r"\b(?:socket|outlet|switch|breaker|bijli|taar|wire|cord)\b", text)
    if spark and device and not _stem_negated(text, spark.start()):
        return "definite", "Electrical hazard"
    if (
        re.search(r"\b(?:pani|paani)\b", text)
        and device
        and re.search(r"\b(?:gir|upar|chingari\w*)\b", text)
        and not (spark and _negated_at(text, spark.start()))
    ):
        return "definite", "Active water"
    if re.search(r"\bganda\b", text) and re.search(r"\b(?:pani|paani)\b", text) and re.search(
        r"\b(?:wapas|aa raha|aa rahi|naale|naali|nali)\b", text
    ):
        return "definite", "Sewage"
    if re.search(r"\besgoto\b", text) and re.search(r"\b(?:voltando|subindo|saindo|transbord\w*|devolv\w*)\b", text):
        return "definite", "Sewage"
    if re.search(r"\b(?:maruming|maduming) tubig\b", text) and re.search(
        r"\b(?:umaakyat|umakyat|kanal|lababo|banyo)\b", text
    ):
        return "definite", "Sewage"
    if re.search(r"\bagua\s+(?:suja|podre|sucia|podrida)\b", text) and re.search(
        r"\b(?:ralo|desague|coladera|drenaje|devolv\w*|subindo|subiendo|saindo)\b", text
    ):
        return "definite", "Sewage"
    if re.search(r"गंदा पानी|गन्दा पानी", text) and re.search(r"आ रहा|ऊपर|वापस|नाली", text):
        return "definite", "Sewage"
    if re.search(r"گندا پانی", text) and re.search(r"آ رہا|اوپر|واپس|نالے", text):
        return "definite", "Sewage"
    if re.search(r"مياه الصرف|مياه المجاري", text) and not re.search(r"لا توجد|بدون", text):
        return "definite", "Sewage"
    if re.search(r"انفجر", text) and re.search(r"خرطوم|أنبوب|ماسورة", text) and re.search(r"ماء|المياه|الماء", text):
        return "definite", "Active water"
    if re.search(r"يملأ|تملأ", text) and re.search(r"ماء|المياه|الماء", text) and re.search(r"غرفة|الغرفة", text):
        return "definite", "Active water"
    if re.search(r"\bpumutok\b", text) and re.search(r"\b(?:tubo|tubig)\b", text):
        return "definite", "Active water"
    if re.search(r"\bpuno\b", text) and re.search(r"\btubig\b", text) and re.search(r"\b(?:kusina|banyo|sahig)\b", text):
        return "definite", "Active water"
    if re.search(r"चिंगार", text) and re.search(r"स्विच|सॉकेट|पंख|पैनल", text):
        return "definite", "Electrical hazard"
    if re.search(r"الماء|ماء", text) and re.search(r"المصابيح|أضواء", text) and re.search(r"ينزل|يسقط|السقف", text):
        return "definite", "Electrical hazard"
    if re.search(r"أكسيد الكربون|أول أكسيد|اول اكسيد", text) and re.search(r"صداع|دوخة|غثيان|قيء|دوار", text):
        return "definite", "Carbon monoxide"
    if (
        re.search(r"شرارات|شرارة", text)
        and re.search(r"مقبس|قابس|لوحة", text)
        and not re.search(r"لا توجد|ليست هناك|بدون", text)
    ):
        return "definite", "Electrical hazard"
    if re.search(r"انفجر", text) and re.search(r"أنبوب|ماسورة", text) and re.search(r"ماء|المياه", text):
        return "definite", "Active water"
    if re.search(r"गैस|گیس", text) and re.search(r"गंध|बदबू|بو", text) and not re.search(r"नहीं|نہیں", text):
        return "definite", "Gas"
    return None


def _seasonal_dust(text: str) -> bool:
    """Dust or a musty smell when the heat first starts is not a fire."""
    if re.search(r"\b(?:sparks?|sparking|smoke|smoking)\b", text):
        return False
    if _DUSTY_SEASON.search(text):
        return True
    dust = re.search(r"\b(?:dusty|musty|burning[- ]dust|warm dust|smells like dust)\b", text)
    when = re.search(
        r"\b(?:first (?:cold|heating|time)|each october|every (?:year|october|winter|fall)|"
        r"for a (?:minute|hour)|season|heating day)\b",
        text,
    )
    return bool(dust and when)


def _declared_no_leak(text: str) -> bool:
    """'koi leak nahi' is a price question, not a leak that is happening."""
    if _gas_happening(text) or _live_force(text):
        return False
    return bool(re.search(r"\bkoi\b.{0,40}\b(?:nahi|nahin)\b", text))


def _mild_comfort_only(text: str) -> bool:
    """No heat or no cooling, without a vulnerable person and without extreme temperature."""
    loss = bool(_COMFORT.search(text) or _COMFORT_ALT.search(text) or _LOSS_I18N.search(text))
    if re.search(r"\b(?:not cooling|no cooling|is not cooling|isn't cooling|won't cool|wont cool)\b", text):
        loss = True
    if re.search(r"aire no|no enfria", text):
        loss = True
    if not loss or _comfort_bundle(text):
        return False
    if _VULNERABLE.search(text) or _older_adult(text) or _PERSON_I18N.search(text) or _extreme_temperature(text):
        return False
    return True


def _name_only_turn(text: str) -> bool:
    """A turn that is only a person name. It is not a water or gas event."""
    raw = " ".join((text or "").split())
    if not raw or any(ch.isdigit() for ch in raw):
        return False
    words = [word.strip(".,;:!?\"'") for word in raw.split()]
    if not 2 <= len(words) <= 6:
        return False
    particles = {
        "ur", "bin", "ibn", "bint", "van", "von", "de", "da", "di", "del", "della",
        "dos", "das", "du", "la", "le", "el", "al", "ter", "ten", "den", "der", "af",
    }
    for word in words:
        core = word.lower()
        if core in particles:
            continue
        if not word[:1].isupper() or not core.isalpha():
            return False
    return True


def _slot_shaped(text: str) -> bool:
    """A name, a phone, or a street by itself is not a present hazard clause."""
    raw = " ".join((text or "").split())
    if _present_hazard_clause(prepare(raw)):
        return False
    if _name_only_turn(raw):
        return True
    digits = re.sub(r"\D", "", raw)
    letters = re.sub(r"[^A-Za-z]", "", raw)
    if len(digits) >= 10 and len(letters) <= 16:
        return True
    number_words = re.findall(
        r"\b(?:zero|oh|one|two|three|four|five|six|seven|eight|nine|double)\b",
        raw,
        flags=re.I,
    )
    if len(number_words) >= 7:
        return True
    try:
        from app.agent.nlu import extract_street

        street = extract_street(raw)
    except Exception:
        street = None
    if street and len(re.sub(r"[^A-Za-z0-9]", "", street)) >= 8:
        rest = re.sub(re.escape(street), " ", raw, count=1, flags=re.I)
        rest = re.sub(r"\b(?:austin|texas|tx)\b|\d{5}|[,.]", " ", rest, flags=re.I)
        rest = re.sub(
            r"\b(?:zero|oh|one|two|three|four|five|six|seven|eight|nine|double)\b",
            " ",
            rest,
            flags=re.I,
        )
        if len(re.findall(r"[A-Za-z]{4,}", rest)) <= 1:
            return True
    return bool(
        re.fullmatch(
            r"(?:\d{1,6}\s+)?[\w.'’\-]+(?:\s+[\w.'’\-]+){0,5}\s+"
            r"(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|way|court|ct|calle|rua|avenida)\.?"
            r"(?:\s+\d{1,6})?",
            raw,
            flags=re.I,
        )
    )


def _class_name_only(text: str) -> bool:
    """Roleplay or an instruction that only names an emergency class."""
    return bool(_INSTRUCTION.search(text)) and not _described_hazard(text)


def _too_thin(text: str) -> bool:
    """Punctuation and one-letter noise are not a present hazard clause."""
    letters = re.findall(r"[^\W\d_]", text or "", flags=re.UNICODE)
    return len(letters) < 2


def _dialog_act(text: str) -> bool:
    """A yes, a greeting, or a slot pick. Not something happening at the property."""
    raw = " ".join((text or "").split())
    if not raw:
        return False
    return bool(
        re.fullmatch(
            r"(?:hmm+|uh+|um+|hello|hi|hey|thanks|thank you|yes|yeah|yep|yup|no|nope|nah|ok|okay|sure|"
            r"nao|não|nahi|nahin|si|sí|sim|haan|han|"
            r"the earliest(?: you have)?|earliest|the first one|the second one|"
            r"tomorrow(?: morning| afternoon| evening)?|today|that works|book it|please|correct|right|soonest)"
            r"[.!]?",
            raw,
            flags=re.I,
        )
    )


_SCHEDULE_TURN = re.compile(
    r"\b(?:tomorrow|today|tonight|monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"lunes|martes|miercoles|jueves|viernes|sabado|domingo|"
    r"manana|por la tarde|por la noche|"
    r"next week|this week|after lunch|lunchtime|two weeks|"
    r"mid[- ]?(?:january|february|march|april|may|june|july|august|september|october|november|december)|"
    r"end of the month|"
    r"(?:the )?(?:first|second|third|fourth) one|"
    r"(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}|"
    r"the \d{1,2}(?:st|nd|rd|th)|\d{1,2}(?:st|nd|rd|th)|"
    r"earliest|soonest)\b",
    re.I,
)
_FILLER_WORD = {
    "asdf", "qwerty", "blah", "hmm", "uh", "um", "hello", "hi", "hey", "thanks",
    "still", "nothing", "useful", "foo", "bar", "xyz", "aaa", "test",
}
_FUNCTION_WORD = {
    "a", "an", "the", "this", "that", "it", "is", "are", "am", "was", "were", "be",
    "to", "of", "and", "or", "but", "for", "with", "on", "in", "at", "my", "your",
    "we", "i", "you", "just", "only", "please", "not", "no", "so", "um", "uh",
    "yes", "yeah", "ok", "okay", "from", "up", "ma'am", "maam", "sir", "mam",
}


def _content_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", (text or "").lower())


def _schedule_pick(text: str) -> bool:
    """A turn that only names a day or a slot. Not a sentence with a hazard in it."""
    raw = " ".join((text or "").split())
    if _present_hazard_clause(prepare(raw)):
        return False
    if not raw or len(raw) > 80 or not _SCHEDULE_TURN.search(raw):
        return False
    scrub = _SCHEDULE_TURN.sub(" ", raw)
    scrub = re.sub(
        r"\b(?:at|in|the|on|a|an|from|sometime|morning|afternoon|evening|am|pm|"
        r"please|anything|after|before|next|this|week|send|someone|"
        r"el|la|los|las|por|del|al|para|quiero|favor|unas|una|un|works|still|have|if|you)\b",
        " ",
        scrub,
        flags=re.I,
    )
    scrub = re.sub(r"\d+", " ", scrub)
    return len(re.findall(r"[A-Za-z]{3,}", scrub)) <= 1


def _booking_admin(text: str) -> bool:
    """Cancel, reschedule, a callback, or a spoken correction of a slot already given."""
    raw = text or ""
    if _HAZARD_STEM.search(raw) or _fire_or_smoke(raw) or _gas_happening(raw):
        return False
    if re.search(r"\b(?:cancel|reschedul\w*|appointment|which (?:one|appointment))\b", raw, re.I):
        return True
    if re.search(r"\b(?:never ?mind|gotta go|got to go|have to go|i gotta)\b", raw, re.I):
        return True
    if re.search(r"\b(?:call me back|callback|call back)\b", raw, re.I):
        return True
    if len(raw) > 80:
        return False
    if re.search(r"\b\d{3,5}\s+not\s+\d{3,5}\b", raw):
        return True
    if re.search(r"\b\d{3,5}\b", raw) and re.search(r"\b(?:at the end|ends in)\b", raw, re.I):
        return True
    if re.search(r"\b(?:sorry(?:,\s*it'?s| i meant)|i meant|actually it'?s)\b", raw, re.I):
        return True
    return False


def _filler_turn(text: str) -> bool:
    words = _content_words(text)
    if not words or len(words) > 8:
        return False
    allowed = _FILLER_WORD | _FUNCTION_WORD
    return all(word in allowed for word in words)


def _function_only(text: str) -> bool:
    words = _content_words(text)
    return bool(words) and len(words) <= 8 and all(word in _FUNCTION_WORD for word in words)


def _ordinary_fixture(text: str) -> bool:
    """A toilet, faucet, drain, or disposal that runs, drips, or clogs is a job."""
    if (
        _fire_or_smoke(text)
        or _gas_happening(text)
        or _sewage_active(text)
        or _structural_water(text)
        or _co_alarm_and_symptom(text)
        or _comfort_bundle(text)
    ):
        return False
    if re.search(
        r"\b(?:spray\w*|gush\w*|pour\w*|flood\w*|burst\w*|ceiling|sparks?|smoke|sewage|flames?)\b",
        text,
    ):
        return False
    if _FAST_WATER.search(text) or re.search(r"\bmore than a drip\b", text):
        return False
    if re.search(r"\b(?:pushing|upward|sheeting)\b", text) and re.search(r"\bwater\b", text):
        return False
    if re.search(r"\b(?:blowing warm|warm air|needs a flush)\b", text):
        if not _VULNERABLE.search(text) and not _older_adult(text) and not _extreme_temperature(text):
            return True
    if re.search(r"\b(?:exhaust|fan|pump|sump)\b", text) and re.search(r"\b(?:loud|noisy|noise|humming)\b", text):
        return True
    fixture = re.search(
        r"\b(?:toilet|faucet|sink|tub|bathtub|shower|disposal|lavatory|spigot|drain|garbage)\b",
        text,
    )
    motion = re.search(
        r"\b(?:running|runs|dripp\w*|drip\w*|leak\w*|clog\w*|slow|jammed|draining|"
        r"backed|backing|won't stop|wont stop|will not stop|keeps|humming|spinning)\b",
        text,
    )
    return bool(fixture and motion)


def _resolved_alarm(text: str) -> bool:
    if not re.search(r"\b(?:alarm|detector)\b", text):
        return False
    if re.search(r"\b(?:sounding|going off|won't quit|wont quit|will not quit|screaming|collapsed|dizzy)\b", text):
        return False
    return bool(re.search(r"\b(?:stopped|has stopped|and it stopped|false alarm)\b", text))


def _vague_smell(text: str) -> bool:
    """A smell with no gas, smoke, or sewage class. It stays a safety question."""
    if not re.search(r"\b(?:smell\w*|odor\w*|odour\w*)\b", text):
        return False
    if _gas_happening(text) or _fire_or_smoke(text) or _sewage_active(text):
        return False
    if re.search(r"\b(?:rotten eggs?|sulfur|sulphur|gas|smoke|spark\w*)\b", text):
        return False
    return True


def _framed_name_turn(text: str) -> bool:
    """Filler plus a person name. Not a sentence that also describes a hazard."""
    raw = text or ""
    if (
        len(raw) > 120
        or not re.search(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", raw)
        or _HAZARD_STEM.search(raw)
        or _fire_or_smoke(raw)
        or _gas_happening(raw)
    ):
        return False
    try:
        from app.agent.nlu import guess_bare_name
    except Exception:
        return False
    name = guess_bare_name(raw, framed=True)
    if not name or len(name.split()) < 2:
        return False
    rest = re.sub(re.escape(name), " ", raw, count=1, flags=re.I)
    words = _content_words(rest)
    filler = _FILLER_WORD | _FUNCTION_WORD | {
        "hold", "sorry", "dog", "well", "wife", "says", "call", "name", "meant",
        "actually", "correction", "its", "it's", "okay",
    }
    return bool(words) and all(word in filler or len(word) <= 3 for word in words)


def _code_turn(text: str) -> bool:
    """Markup or a SQL fragment is not a present hazard clause."""
    if _HAZARD_STEM.search(text) or _fire_or_smoke(text) or _gas_happening(text):
        return False
    return bool(re.search(r"drop\s+table|<script|</\w+>|fetch\s*\(|;\s*--|%\{", text, re.I))


def _spam_turn(text: str) -> bool:
    if _HAZARD_STEM.search(text) or _fire_or_smoke(text) or _gas_happening(text):
        return False
    try:
        from app.agent.nlu import is_spam
    except Exception:
        return False
    return bool(is_spam(text))


def _booking_request(text: str) -> bool:
    """A caller asking to book, with no hazard clause in the same turn."""
    if _present_hazard_clause(text):
        return False
    return bool(
        re.search(
            r"\b(?:book|schedule|quote|install|replace|repair|service|maintenance|appointment|estimate|hook\s?up|inspect\w*|re-?check\w*)\b",
            text,
            re.I,
        )
    )


_PHYSICAL_CHANGE = re.compile(
    r"\b(?:dark|damp|wet|brown|black|new|weird)\s+(?:mark|stain|spot|patch)\b|"
    r"\b(?:mark|stain|spot|patch)\b.{0,48}\b(?:ceiling|wall|drywall)\b|"
    r"\b(?:ceiling|wall|drywall)\b.{0,48}\b(?:mark|stain|spot|patch)\b|"
    r"\b(?:boiler|heater|furnace|water heater)\b.{0,56}\bknock\w*\b|"
    r"\bknock\w*\b.{0,56}\b(?:boiler|heater|furnace|water heater)\b",
    re.I,
)


def _physical_change(text: str) -> bool:
    """A mark or a knock with no present hazard. It stays a safety question."""
    if not (text or "").strip() or not _PHYSICAL_CHANGE.search(text):
        return False
    if _present_hazard_clause(text) or _WATER_FORCE.search(text):
        return False
    if _sewage_active(text) or _sounding_detector(text) or _uncontrolled_water(text):
        return False
    if _gas_happening(text) or _fire_or_smoke(text) or _rotten_or_dizzy(text) or _comfort_bundle(text):
        return False
    return True


def _missed_hazard_shape(text: str) -> bool:
    """Dirty water or a howling unit the present-hazard check should already own.

    Used so a high head is not cleared when that check misses the wording.
    """
    if _sewage_active(text) or _sounding_detector(text) or _uncontrolled_water(text):
        return True
    if _gas_happening(text) or _fire_or_smoke(text) or _comfort_bundle(text):
        return True
    if re.search(
        r"\b(?:aguas?\s+sucias?|aguas?\s+podridas?|aguas?\s+sujas?|aguas?\s+podres?|"
        r"maduming tubig|maruming tubig|brown water|black water|raw sewage|esgoto)\b",
        text or "",
        re.I,
    ):
        return True
    if re.search(r"गंदा पानी|گندا پانی|مياه المجاري|مياه الصرف", text or ""):
        return True
    if re.search(r"\bganda\b", text or "", re.I) and re.search(r"\b(?:pani|paani)\b", text or "", re.I):
        return True
    if _DETECTOR_HOWL.search(text or "") and _HOWL_SOURCE.search(text or "") and (
        _ILLNESS.search(text or "") or _symptom_live(text or "")
    ):
        return True
    return False


def _vague_menu_turn(text: str, original: str = "") -> bool:
    """English filler that names neither a job nor a hazard. It must not page."""
    if _physical_change(text):
        return False
    if _present_hazard_clause(text) or _WATER_FORCE.search(text or ""):
        return False
    if _present_hazard_clause(text) or _uncontrolled_water(text) or _sounding_detector(text):
        return False
    try:
        from app.agent.nlu import detect_language

        if detect_language(original or text) != "en":
            return False
    except Exception:
        return False
    if _HAZARD_NOUN.search(text) or _HAZARD_STEM.search(text):
        return False
    if re.search(
        r"\b(?:smell\w*|odor\w*|smoke|gas|spark\w*|alarm|flood|sewage|outlet|panel|dizzy|flame\w*|leak\w*|burst\w*)\b",
        text,
    ):
        return False
    if _plain_job(text) or _catalogue_job(text) or _ORDINARY_JOB.search(text) or _booking_request(text):
        return False
    words = _content_words(text)
    return 0 < len(words) <= 16


def _fast_routine(text: str) -> bool:
    """Recognized non-emergencies. Used to skip a second model, never to skip the head."""
    if _present_hazard_clause(text):
        return False
    if (
        _present_patterns(text)
        or _fire_or_smoke(text)
        or _gas_happening(text)
        or _sewage_active(text)
        or _co_alarm_and_symptom(text)
        or _comfort_bundle(text)
        or _structural_water(text)
    ):
        return False
    return bool(
        _ordinary_fixture(text)
        or _schedule_pick(text)
        or _booking_admin(text)
        or _filler_turn(text)
        or _function_only(text)
        or _framed_name_turn(text)
        or _spam_turn(text)
        or _code_turn(text)
        or _resolved_alarm(text)
    )


def _blocks_head_page(text: str) -> bool:
    """A recognized non-emergency. The head may not page or ask over it.

    An unrecognized line can still page from the head. A clearance the rules
    already understand cannot: a plain job, a mild drip, a negated leak,
    seasonal dust, a comfortable house, or comfort loss without a vulnerable person.
    Uncontrolled water and a howling detector are not clearances.
    """
    if _present_hazard_clause(text) or _uncontrolled_water(text) or _sounding_detector(text):
        return False
    if _policy_floor(text)[0] == "definite":
        return False
    if _compose_definite(text) is not None or _present_patterns(text) is not None:
        return False
    if _situational_hazard(text) is not None or _co_alarm_and_symptom(text):
        return False
    if _fire_or_smoke(text) or _gas_happening(text) or _sewage_active(text):
        return False
    if _structural_water(text):
        return False
    if _fast_routine(text):
        return True
    if _live_force(text):
        return False
    if (
        _habitual_mild(text)
        or _routine_context(text)
        or _plain_job(text)
        or _explicit_clear(text)
        or _dry_trap(text)
        or _plain_fixture(text)
        or _routine_service(text)
        or _contained_appliance_water(text)
        or _mild_water(text)
        or _sink_backup(text)
        or _only_negated_gas(text)
        or _catalogue_job(text)
        or _seasonal_dust(text)
        or _declared_no_leak(text)
        or _mild_comfort_only(text)
        or _benign_home_talk(text)
        or framed_entirely_away(text)
    ):
        return True
    return False


def _benign_home_talk(text: str) -> bool:
    """Maintenance, a reschedule, or a comfortable house. Not a live hazard."""
    if _fire_or_smoke(text) or _gas_happening(text) or _live_force(text) or _sewage_active(text):
        return False
    if re.search(r"\b(?:sparks?|sparking|smoke|smoking|flood\w*|burst\w*|sewage|monoxide|alarm)\b", text):
        return False
    if re.search(
        r"\b(?:filter|return vent|sprinkler|blower|disposal|ice ?maker|air handler|"
        r"already booked|move a diagnostic|reschedul\w*|locked myself)\b",
        text,
    ):
        return True
    if re.search(r"\b(?:house|casa|home)\b", text) and re.search(r"\b(?:6[5-9]|7[0-9]|8[0-4])\b", text):
        if not _VULNERABLE.search(text) and not _older_adult(text) and not _extreme_temperature(text):
            return True
    return False


def _policy_floor(text: str) -> tuple[str, str | None]:
    """Composition that can only raise a turn. It does not clear one."""
    active = _active_context(text) or ""
    if _sounding_detector(active):
        return "definite", "Carbon monoxide"
    if _uncontrolled_water_now(active):
        return "definite", "Active water"
    if _co_alarm_and_symptom(text):
        return "definite", "Carbon monoxide"
    if _comfort_bundle(text):
        return "definite", "Unsafe indoor temperature"
    composed = _multilingual_compose(text)
    if composed is not None:
        return composed
    if _noun_active_ask(text) or _appliance_flicker(text):
        return "ask", "Uncertain hazard"
    return "none", None


def _emergency_probability(text: str) -> float | None:
    try:
        from app.agent.hazard_head import hazard_probs
    except Exception:
        return None
    probs = hazard_probs(text)
    if probs is None:
        return None
    return float(probs[0])


def _rotten_or_dizzy(text: str) -> bool:
    """A rotten-egg odor or dizziness is a page, not a vague smell."""
    if re.search(r"चक्कर|چکر|دوران", text or ""):
        return True
    return bool(
        re.search(
            r"\b(?:rotten eggs?|sulfur|sulphur|huevo podrido|ovo podre|"
            r"dizzy|dizziness|mareo|mareada|nahihilo|chakkar|nauseous|nauseated)\b",
            text or "",
            re.I,
        )
    )


def _emergency_word_only(text: str) -> bool:
    """True when the only hazard signal is the word emergency."""
    if not _EMERGENCY_WORD.search(text or ""):
        return False
    bare = _scrub_emergency_word(text or "")
    if _live_physical(bare) or _uncontrolled_water(bare) or _sounding_detector(bare):
        return False
    if _sewage_active(bare) or _gas_happening(bare) or _fire_or_smoke(bare) or _smoke_happening(bare):
        return False
    return True


def _routine_clearance(prepared: str, original: str) -> bool:
    """A real routine: a schedule, a booking, a mild drip, a catalogue job.

    Spanish intent is not in this list. A job word alone must not clear a
    head that present-hazard failed to explain.
    """
    if _schedule_pick(original) or _schedule_pick(prepared):
        return True
    if _filler_turn(original) or _filler_turn(prepared) or _dialog_act(original) or _too_thin(original):
        return True
    if _slot_shaped(original) or _framed_name_turn(original) or _spam_turn(original) or _code_turn(prepared):
        return True
    if _instruction_only(prepared) or _class_name_only(prepared):
        return True
    if _catalogue_job(prepared) or _ordinary_fixture(prepared) or _plain_job(prepared):
        return True
    if _mild_water(prepared) or _booking_request(prepared) or _booking_admin(prepared):
        return True
    if _fast_routine(prepared):
        return True
    if (
        _habitual_mild(prepared)
        or _routine_context(prepared)
        or _explicit_clear(prepared)
        or _dry_trap(prepared)
        or _routine_service(prepared)
        or _contained_appliance_water(prepared)
        or _only_negated_gas(prepared)
        or _seasonal_dust(prepared)
        or _declared_no_leak(prepared)
        or _mild_comfort_only(prepared)
        or _benign_home_talk(prepared)
        or framed_entirely_away(prepared)
        or framed_entirely_away(original)
    ):
        return True
    return False


def _confirmed_safe_routine(prepared: str, original: str) -> bool:
    """A routine whose present-hazard check found no hazard.

    This is the only clearance allowed to zero a head at or above 0.80.
    """
    if _physical_change(prepared) or _missed_hazard_shape(prepared):
        return False
    active = _active_context(prepared) or ""
    if (
        _present_hazard_clause(prepared)
        or _uncontrolled_water_now(active)
        or _sounding_detector(active)
        or _sewage_active(active)
        or _gas_happening(prepared)
        or _fire_or_smoke(prepared)
        or _comfort_bundle(prepared)
    ):
        return False
    if _routine_clearance(prepared, original):
        return True
    # A Spanish job can clear a high head only after the checks above found
    # no sewage, no howling unit, and no other present hazard.
    try:
        from app.agent.nlu import _spanish_intent

        return _spanish_intent(original) in {"new_job", "quote", "existing_booking"}
    except Exception:
        return False


def _hard_routine(prepared: str, original: str) -> bool:
    """A recognized routine with no present hazard. It may clear a head under 0.80.

    A vague-menu match is not one of these. A mild drip is, until the same
    turn has uncontrolled water, sewage, or a sounding unit.
    """
    active = _active_context(prepared) or ""
    if (
        _present_hazard_clause(prepared)
        or _uncontrolled_water_now(active)
        or _sounding_detector(active)
        or _sewage_active(active)
        or _missed_hazard_shape(prepared)
    ):
        return False
    if _routine_clearance(prepared, original):
        return True
    try:
        from app.agent.nlu import _spanish_intent

        if _spanish_intent(original) in {"new_job", "quote", "existing_booking"}:
            return True
    except Exception:
        return False
    return False


def names_neither_job_nor_hazard(text: str) -> bool:
    """The caller named no job and no hazard. Do not store the turn as the issue."""
    raw = text or ""
    prepared = prepare(raw)
    if _present_hazard_clause(prepared) or _uncontrolled_water(prepared) or _sounding_detector(prepared):
        return False
    if _sewage_active(prepared) or _gas_happening(prepared) or _fire_or_smoke(prepared):
        return False
    if _plain_job(prepared) or _catalogue_job(prepared) or _ordinary_fixture(prepared):
        return False
    if _ORDINARY_JOB.search(prepared) or _mild_water(prepared) or _booking_request(prepared):
        return False
    if _HAZARD_NOUN.search(prepared) or _HAZARD_STEM.search(prepared):
        return False
    if re.search(
        r"\b(?:flush|heaters?|heeder|heder|furnace|boiler|toilet|faucet|aerator|drain|disposal|filter|"
        r"thermostat|install\w*|replace\w*|repair\w*|fix|quote|appointment|tune-?up|"
        r"vanity|spout|spigot|softener|sump|caulk\w*|shower|clog\w*|leak\w*|drip\w*|"
        r"maintenance|water heater|hot water|come out|heat\s*pump|yearly|annual|"
        r"check|ac|a/c|cooling|not cooling)\b",
        prepared,
        re.I,
    ):
        return False
    try:
        from app.agent.nlu import _spanish_intent, service_catalogue

        if service_catalogue(raw):
            return False
        if _spanish_intent(raw) in {"new_job", "quote", "existing_booking"}:
            return False
    except Exception:
        return False
    return True


def classify_emergency(text: str) -> tuple[str, str | None]:
    """Score the learned head on every turn. Word lists may only raise.

    A routine clearance may block a page. An instruction that only names an
    emergency class may not escalate. A bare name or a street may not page.
    A chirp without a live symptom stays advice. If the head checkpoint is
    missing, a turn the rules do not already understand asks the safety
    question instead of opening the generic menu.
    """
    rules = rules_screen(text)
    prepared = prepare(text)
    floor = _policy_floor(prepared)
    from app.agent.hazard_head import head_level

    head = head_level(text)
    if _negated_clear(text) or _negated_clear(prepared):
        # A no-danger answer must not page, even when stripping the negation
        # would leave the word danger behind.
        return "none", None
    if rules[0] == "advice" and floor[0] != "definite" and not _symptom_live(prepared):
        return rules
    if _class_name_only(prepared):
        # Naming a class can ask. It cannot page unless a present hazard remains.
        if rules[0] in {"ask", "advice"}:
            return rules
        return "none", None
    if _framed_name_turn(text) and floor[0] != "definite" and rules[0] != "definite":
        # prepare() lowercases, so the name check has to see the caller's capitals.
        return "none", None
    if _slot_shaped(text) and floor[0] != "definite" and rules[0] != "definite":
        return "none", None
    if (_dialog_act(text) or _too_thin(text)) and floor[0] != "definite" and rules[0] != "definite":
        return "none", None
    if head is None:
        raised = _stricter(rules, floor)
        if raised[0] in {"definite", "advice", "ask"}:
            return raised
        if _blocks_head_page(prepared):
            return "none", None
        return "ask", "Hazard model unavailable"
    head_score = _emergency_probability(text) if head is not None else None
    high_head = head[0] == "definite" and head_score is not None and head_score >= 0.80
    if head[0] == "definite" and _emergency_word_only(prepared):
        # Saying "emergency" inside a booking or an instruction is not a page.
        head = ("none", None)
    elif high_head:
        # Keep a definite head before catalogue, plain-job, mild-drip, or
        # Spanish intent can clear it. A clearance may zero this head only
        # after present-hazard has confirmed a real routine. If that check
        # misses, page. A mark or a knock, and a vague menu, stay a question.
        if _confirmed_safe_routine(prepared, text):
            head = ("none", None)
        elif _physical_change(prepared) or _vague_menu_turn(prepared, text):
            head = ("ask", "Uncertain hazard")
        else:
            pass
    elif head[0] == "definite" and _hard_routine(prepared, text):
        head = ("none", None)
    elif head[0] == "definite" and not _present_hazard_clause(prepared):
        if _physical_change(prepared):
            head = ("ask", head[1] or "Uncertain hazard")
        elif (
            _vague_menu_turn(prepared, text)
            or _schedule_pick(text)
            or _schedule_pick(prepared)
            or _instruction_only(prepared)
            or _filler_turn(text)
            or _filler_turn(prepared)
            or _dialog_act(text)
            or _booking_request(prepared)
            or _slot_shaped(text)
        ):
            head = ("none", None)
        elif _blocks_head_page(prepared):
            head = ("none", None)
    elif head[0] == "definite" and _blocks_head_page(prepared):
        head = ("none", None)
    if (
        head[0] == "definite"
        and floor[0] != "definite"
        and not _rotten_or_dizzy(prepared)
        and (
            _lone_category(prepared)
            or (rules[0] == "ask" and rules[1] == "Uncertain hazard")
            or (_vague_smell(prepared) and rules[0] != "definite")
        )
    ):
        # A bare noun, a damp spot, a rumble, or a smell with no class stays a question.
        # A named gas, water, or carbon-monoxide ask is raised when the head pages.
        head = ("ask", head[1] or "Uncertain hazard")
    base = rules if head[0] == "none" else _stricter(rules, head)
    if base[1] == "Hazard" and rules[0] == "definite" and rules[1] not in {None, "Hazard"}:
        base = rules
    result = _stricter(base, floor)
    if result[1] == "Hazard" and floor[0] == "definite" and floor[1] not in {None, "Hazard"}:
        result = floor
    if result[1] == "Hazard" and rules[0] == "definite" and rules[1] not in {None, "Hazard"}:
        result = rules
    if result[1] == "Caller said emergency" or (
        result[0] == "definite" and _emergency_word_only(prepared)
    ):
        result = ("none", None)
    if _physical_change(prepared) and result[0] in {"definite", "none"}:
        # A ceiling mark or a knocking boiler stays on the safety question.
        return "ask", "Uncertain hazard"
    if high_head and result[0] == "none" and not _confirmed_safe_routine(prepared, text):
        # Present-hazard missed and this is not a real routine. Do not book it.
        return "ask", "Uncertain hazard"
    if (
        result[0] == "none"
        and not _recognized_clear(prepared, text)
        and _under_cut_candidate(prepared)
    ):
        # Under the page cut, and not a routine job: ask. Do not open the menu.
        return "ask", "Uncertain hazard"
    return result


def _negated_clear(text: str) -> bool:
    """A natural no that names danger only to deny it."""
    if not _NEGATED_CLEAR.search(text or ""):
        return False
    scrub = _NEGATED_CLEAR.sub(" ", text or "")
    scrub = re.sub(
        r"\b(?:danger|emergency|peligro|perigo|panganib|khatra|delikado)\b",
        " ",
        scrub,
        flags=re.I,
    )
    scrub = re.sub(r"خطر|खतरा|خطرہ|يوجد|هناك", " ", scrub)
    if not scrub.strip():
        return True
    return not _present_hazard_clause(prepare(scrub))


_UNDER_CUT_DOMAIN = re.compile(
    r"\b(?:outlets?|panels?|breakers?|smoke|smoking|gas|sparks?|sparking|alarms?|"
    r"smells?|odou?rs?|dizzy|flames?|burst\w*|flood\w*|sewage|hiss\w*|"
    r"usok|sunog|dhuan|boo+|humo|fuma[cç]a|enchufe|chispas?)\b",
    re.I,
)


def _under_cut_candidate(text: str) -> bool:
    """A line that might be a hazard the rules did not already clear.

    A negated leak, an emergency-fund question, or a school poster is not one.
    """
    if _present_hazard_clause(text):
        return True
    return any(not _negated_at(text, match.start()) for match in _UNDER_CUT_DOMAIN.finditer(text))


def _recognized_clear(prepared: str, original: str) -> bool:
    """A routine, a slot, filler, or a vague English line. Not a missed hazard."""
    if _present_hazard_clause(prepared):
        return False
    if _blocks_head_page(prepared) or _fast_routine(prepared):
        return True
    if _filler_turn(original) or _filler_turn(prepared):
        return True
    if _dialog_act(original) or _too_thin(original):
        return True
    if _slot_shaped(original) or _schedule_pick(original) or _schedule_pick(prepared):
        return True
    if _framed_name_turn(original) or _spam_turn(original) or _code_turn(prepared):
        return True
    if _class_name_only(prepared) or _instruction_only(prepared):
        return True
    if _vague_menu_turn(prepared, original) or _booking_request(prepared):
        return True
    if _mild_water(prepared) or _ordinary_fixture(prepared):
        return True
    if framed_entirely_away(prepared) or framed_entirely_away(original):
        return True
    try:
        from app.agent.nlu import _spanish_intent

        if _spanish_intent(original) in {"new_job", "quote", "existing_booking"}:
            return True
    except Exception:
        pass
    return False


_NEGATED_CLEAR = re.compile(
    r"\bno danger\b|\bnot in danger\b|\bno one is (?:in )?(?:any )?danger\b|"
    r"\bnobody is (?:in )?danger\b|"
    r"\bno hay peligro\b|\bnadie en peligro\b|\bsin peligro\b|"
    r"\bn[aã]o h[aá] perigo\b|\bn[aã]o tem perigo\b|\bsem perigo\b|\bningu[eé]m em perigo\b|"
    r"\bwalang panganib\b|\bhindi delikado\b|"
    r"\bkoi khatra nahi\b|\bkhatra nahi\b|\bkoi khatre mein nahi\b|"
    r"لا يوجد خطر|لا خطر|ليس هناك خطر|ما في خطر|"
    r"कोई खतरा नहीं|खतरा नहीं|"
    r"کوئی خطرہ نہیں|خطرہ نہیں",
    re.I,
)


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
