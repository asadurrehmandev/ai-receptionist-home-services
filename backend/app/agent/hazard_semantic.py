"""Multilingual hazard second opinion.

Uses paraphrase-multilingual-MiniLM-L12-v2 (fastembed, 384-d, mean pooling
in 0.6.1). Each concept is a margin between hazard prototypes and routine
near-misses. The concept rules remain the floor. This layer can only add
urgency. Thresholds are calibrated after the frozen set is written.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Calibrated after the frozen set was frozen. See README for the pre-tune score.
DEFINITE_COSINE = 0.78
DEFINITE_MARGIN = 0.045
ASK_COSINE = 0.70
ASK_MARGIN = 0.02

_LABELS = {
    "gas": "Gas",
    "co": "Carbon monoxide",
    "water": "Active water",
    "electrical": "Electrical hazard",
    "comfort": "Unsafe indoor temperature",
}

_HAZARD = {
    "gas": [
        "I smell gas",
        "gas odor in the house",
        "rotten egg smell indoors",
        "hissing gas line",
        "gas is leaking",
        "propane leak inside",
        "natural gas smell",
        "sulfur smell near the meter",
        "gas leaking from a pipe",
        "strong gas odor right now",
        "the room smells like gas",
        "gas escaping indoors",
        "odeur de gaz",
        "ça sent le gaz",
        "fuite de gaz",
        "riecht nach Gas",
        "Gasgeruch im Haus",
        "Gas tritt aus",
        "cheiro de gás",
        "vazamento de gás",
        "olor a gas",
        "huele a gas",
        "fuga de gas",
        "запах газа",
        "пахнет газом",
        "утечка газа",
        "煤气泄漏",
        "有煤气味",
        "家里有煤气味",
        "가스 냄새",
        "가스가 새다",
        "가스 냄새가 난다",
        "厨房有煤气",
        "闻到煤气",
        "煤气味道很重",
        "屋子里全是煤气",
        "煤气泄漏了",
        "mùi gas",
        "có mùi khí gas",
        "gas cheira mal",
        "pachnie gazem",
        "zapach gazu",
        "odore di gas",
        "fuga di gas",
        "gaslek in huis",
        "ik ruik gas",
    ],
    "co": [
        "carbon monoxide alarm sounding",
        "CO alarm will not stop",
        "carbon monoxide detector going off",
        "people feel sick and the furnace is on",
        "headache dizzy furnace",
        "high ppm carbon monoxide",
        "monoxide alarm screaming",
        "CO detector beeping continuously",
        "alarma de monoxido sonando",
        "detector de monoxido no para",
        "alarme de monoxyde",
        "détecteur de monoxyde en alarme",
        "Kohlenmonoxid Alarm",
        "CO Melder piept dauernd",
        "alarme de monóxido tocando",
        "detector de monóxido disparando",
        "угарный газ сигнализация",
        "一氧化碳报警",
        "일산화탄소 경보",
        "báo động khí CO",
        "allarme monossido",
        "koolmonoxide alarm",
        "czujnik czadu wyje",
        "alarm tlenku węgla",
        "the monoxide alarm is screaming",
        "detector reads a high carbon monoxide level",
        "family is nauseous with the heat running",
        "CO alarm sounding in the hallway",
        "monoxide detector will not silence",
        "beeping carbon monoxide alarm",
        "alarma de monóxido de carbono activa",
        "le détecteur de CO sonne",
        "CO-Warner geht nicht aus",
        "alarme de CO não para",
        "сигнализация угарного газа",
        "煤气报警器一直响",
        "일산화탄소 경보기가 울린다",
        "cảnh báo khí CO kêu",
        "people vomiting and the boiler is on",
        "ppm reading on the CO detector",
    ],
    "water": [
        "water pouring through the ceiling",
        "pipe burst and flooding",
        "basement is flooding",
        "water gushing from a pipe",
        "sewage coming up through the floor",
        "raw sewage backup",
        "water will not shut off",
        "active flood in the house",
        "ceiling is raining water",
        "main line burst",
        "inondation dans la maison",
        "cave inondée",
        "l'eau jaillit",
        "Überschwemmung im Haus",
        "Keller unter Wasser",
        "Wasserrohrbruch",
        "inundación en el sótano",
        "se está inundando la casa",
        "tubo reventado",
        "enchente dentro de casa",
        "cano estourado",
        "água jorrando",
        "потоп в квартире",
        "труба прорвало",
        "затопило квартиру",
        "家里发大水",
        "水管爆了",
        "천장에서 물이 쏟아진다",
        "집이 침수됐다",
        "배관이 터졌다",
        "nhà bị ngập",
        "ống nước bị vỡ",
        "allagamento in casa",
        "tubo scoppiato",
        "huis staat onder water",
        "sewage overflowing onto the floor",
        "water shooting out of the wall",
        "the basement is full of water",
        "a supply line burst open",
        "flood water inside the garage",
    ],
    "electrical": [
        "outlet is sparking",
        "sparks from the breaker panel",
        "smoke from an outlet",
        "burning smell from the wiring",
        "electrical fire smell",
        "switch is sparking",
        "panel is smoking",
        "burning plastic from the socket",
        "arcing at the outlet",
        "wires are sparking",
        "chispas en el enchufe",
        "enchufe con chispas",
        "humo del tablero",
        "étincelles sur la prise",
        "prise qui fait des étincelles",
        "fumée du tableau électrique",
        "Funken aus der Steckdose",
        "Steckdose funkt",
        "Brandgeruch aus der Dose",
        "faíscas na tomada",
        "tomada soltando faísca",
        "cheiro de queimado na fiação",
        "искры из розетки",
        "искрит розетка",
        "дым из щитка",
        "插座冒火花",
        "电闸在冒烟",
        "콘센트에서 불꽃이 튄다",
        "차단기에서 연기가 난다",
        "ổ cắm bắn tia lửa",
        "tủ điện bốc khói",
        "scintille dalla presa",
        "quadro elettrico fuma",
        "vonken uit het stopcontact",
        "iskry z gniazdka",
        "dym z tablicy elektrycznej",
        "the light switch is throwing sparks",
        "outlet popping and smoking",
        "breaker buzzing and hot",
        "cord melting at the plug",
    ],
    "comfort": [
        "no heat and a baby in the house",
        "elderly person and the furnace is dead",
        "freezing inside with no heat",
        "infant and the heat is out",
        "house is below 40 degrees and no heat",
        "grandmother and the heater quit",
        "very cold inside and the boiler is out",
        "no heat and someone is shivering",
        "elderly and no air conditioning in extreme heat",
        "indoor temperature is dangerously low",
        "no heat and an oxygen user",
        "pregnant and the heat is out",
        "toddler and the furnace died",
        "it is dangerously cold with no heat",
        "no heat and an older adult",
        "the house is far too cold for a child",
        "no cooling and someone is overheating",
        "heat is out and the home is freezing",
        "vulnerable person without heat",
        "no heat and the indoor temperature is extreme",
        "sin calor y hay un bebé",
        "anciano sin calefacción",
        "pas de chauffage et un bébé",
        "keine Heizung und ein Baby",
        "sem aquecimento e um bebê",
        "нет отопления и ребёнок",
        "没有暖气 老人",
        "난방이 없고 아기가 있다",
        "không có sưởi và có em bé",
        "niente riscaldamento e un neonato",
        "geen verwarming en een baby",
        "brak ogrzewania i niemowlę",
        "freezing house furnace dead",
        "90 year old and no heat",
        "newborn and the heater will not start",
        "hypothermia risk no heat",
        "inside is icy and the heat failed",
        "disabled adult and no heat",
        "no heat and it is well below 50",
        "someone vulnerable is without heat",
    ],
}

_ROUTINE = {
    "gas": [
        "quote for a gas water heater",
        "question about the gas bill",
        "car is out of gas",
        "convert the stove to gas",
        "hook up a gas dryer",
        "gas fireplace install quote",
        "no gas smell",
        "gas appliance estimate",
        "schedule a gas furnace tune up",
        "the gas company already fixed it",
        "old gas leak that was repaired",
        "price of a gas line to the grill",
        "gas range installation estimate",
        "utility gas invoice",
        "devis chauffe-eau gaz",
        "presupuesto de estufa de gas",
        "orçamento aquecedor a gás",
        "Angebot Gastherme",
        "смета на газовый котёл",
        "燃气热水器报价",
        "가스레인지 견적",
        "báo giá bếp gas",
        "preventivo caldaia a gas",
        "offerte gasketel",
        "wycena kuchenki gazowej",
        "no odor at all",
        "pilot light is out with no smell",
        "gas dryer hookup no leak",
        "estimate to move a gas meter",
        "annual gas inspection with no symptoms",
        "the stove is gas and it works",
        "replace a gas valve as a quote",
        "I want a gas cooktop quote",
        "how much to run a gas line",
        "gas logs installation",
        "tankless gas heater estimate",
        "the car ran out of fuel",
        "gas station nearby",
        "billing question for the gas utility",
        "no leak, just a quote",
    ],
    "co": [
        "install a carbon monoxide detector",
        "quote for a CO alarm",
        "buy a monoxide detector",
        "chirp and a low battery",
        "only the battery is chirping",
        "single chirp from the detector",
        "CO alarm needs a new battery",
        "detector is still in the box",
        "unplugged carbon monoxide alarm",
        "where to place a CO detector",
        "price of a monoxide alarm",
        "bring a detector battery",
        "the chirp is just the battery",
        "replace the clock battery not an alarm",
        "smoke alarm battery chirp",
        "devis détecteur de monoxyde",
        "presupuesto detector de monoxido",
        "orçamento detector de monóxido",
        "Angebot CO Melder",
        "купить датчик угарного газа",
        "一氧化碳探测器报价",
        "일산화탄소 경보기 견적",
        "báo giá máy báo CO",
        "preventivo rilevatore CO",
        "offerte koolmonoxidemelder",
        "wycena czujnika czadu",
        "how many detectors do I need",
        "the alarm is not installed yet",
        "battery chirp once a minute",
        "low battery beep on the detector",
        "I have a spare battery for the CO alarm",
        "quote to hardwire a CO detector",
        "no alarm is sounding",
        "the detector is silent",
        "just shopping for an alarm",
        "CO detector for a new build quote",
        "where should I mount the alarm",
        "the beep stopped after I aired the room and it was the battery",
        "no symptoms, only a chirp",
        "catalog price for a plug-in CO alarm",
    ],
    "water": [
        "faucet dripping a little",
        "slow drip under the sink",
        "leaking a little",
        "sink backing up",
        "tub drains slowly",
        "toilet keeps running",
        "low water pressure",
        "garbage disposal jammed",
        "water heater popping no leak",
        "outdoor spigot drip",
        "quote a water softener",
        "ice maker overflowing into the freezer",
        "one drop a minute",
        "drain gurgles",
        "sump pump is loud and the basement is dry",
        "small drip from the shower",
        "washer shakes but does not leak",
        "clogged drain",
        "slow kitchen drain",
        "grifo que gotea",
        "robinet qui goutte",
        "tropft ein bisschen",
        "torneira pingando",
        "медленно стекает раковина",
        "水龙头滴水",
        "수도꼭지가 조금 샌다",
        "vòi nước nhỏ giọt",
        "rubinetto che gocciola",
        "kraan druppelt",
        "kran kapie",
        "estimate to replace a faucet",
        "schedule a drain cleaning",
        "the basement is dry",
        "no active leak",
        "condensation on a pipe",
        "a damp cabinet from a drip",
        "toilet flapper quote",
        "water pressure is low",
        "the sink is slow",
        "backing up into the sink only",
    ],
    "electrical": [
        "thermostat screen is blank",
        "condenser fan wobbles",
        "capacitor replacement price",
        "noisy air conditioner",
        "filter is dirty",
        "light bulb is out",
        "outlet is loose quote",
        "I smelled toast",
        "breaker tripped and the kitchen is fine",
        "want an electrician quote for new lights",
        "the switch is stiff",
        "ceiling fan wobbles",
        "price to add an outlet",
        "smoke from cooking",
        "burnt toast smell",
        "devis prise électrique",
        "presupuesto de enchufe",
        "orçamento de tomada",
        "Angebot Steckdose",
        "смета на розетку",
        "插座报价",
        "콘센트 견적",
        "báo giá ổ cắm",
        "preventivo presa",
        "offerte stopcontact",
        "wycena gniazdka",
        "the panel is quiet",
        "no sparks",
        "lights flicker sometimes quote",
        "GFCI keeps tripping in the garage quote",
        "we want new recessed lights",
        "the doorbell transformer quote",
        "a warm phone charger",
        "cooking smoke from the oven",
        "the lamp cord is old and I want it replaced",
        "estimate to label the breaker panel",
        "no burning smell",
        "the outlet works and I want another one",
        "fan motor hums",
        "quote to move a switch",
    ],
    "comfort": [
        "the AC is not cooling",
        "no heat and the house is comfortable",
        "furnace tune-up",
        "air conditioner is noisy",
        "house is 76 degrees and the AC is not cooling",
        "no heat and it is 68 degrees",
        "maintenance plan for the furnace",
        "thermostat quote",
        "filter change",
        "window unit is not cooling one room",
        "the attic is warm in the afternoon",
        "schedule a heating check",
        "AC not keeping up on a mild day",
        "heater is old and I want a quote",
        "everyone is fine and the house is cool but not cold",
        "el aire no enfría",
        "la clim no refroidit pas",
        "Die Heizung soll gewartet werden",
        "o ar condicionado não gela",
        "кондиционер не холодит",
        "空调不制冷",
        "에어컨이 안 시원해요",
        "máy lạnh không mát",
        "il condizionatore non raffredda",
        "de airco koelt niet",
        "klimatyzacja nie chłodzi",
        "routine no heat call",
        "the heat is weak and it is 70 inside",
        "AC quote for a mild day",
        "furnace is running and the house is fine",
        "no vulnerable person and the house is 72",
        "we want a new thermostat",
        "the blower is loud",
        "seasonal tune up",
        "AC not cooling the spare room only",
        "heat pump quote",
        "the house is 74 and we want it colder",
        "no emergency, just no cooling",
        "comfortable temperature and a noisy unit",
        "schedule maintenance not an emergency",
    ],
}

_model = None
_bank: dict[str, tuple[np.ndarray, np.ndarray]] | None = None
_load_failed = False


class EmbedderUnavailable(RuntimeError):
    """The hazard weights could not be loaded. Callers must fail closed."""


def semantic_ready() -> bool:
    """True only after the local weights have loaded. A failed load is not retried."""
    if _load_failed:
        return False
    if _model is not None:
        return True
    try:
        _embedder()
    except EmbedderUnavailable:
        return False
    return _model is not None


def _person_name_only(text: str) -> bool:
    """A bare name must not be scored against the water or gas prototypes."""
    words = [word.strip(".,;:!?\"'") for word in (text or "").split()]
    if not 2 <= len(words) <= 6 or any(any(ch.isdigit() for ch in word) for word in words):
        return False
    particles = {"ur", "bin", "ibn", "bint", "van", "von", "de", "da", "di", "del", "der", "la", "le", "al"}
    for word in words:
        core = word.lower()
        if core in particles:
            continue
        if not word[:1].isupper() or not core.isalpha():
            return False
    return True


def semantic_hazard(text: str) -> tuple[str, str | None]:
    """Return ('definite'|'ask'|'none', label). Empty and tiny strings are none.

    A missing model asks a person to judge the call. It does not report 'no hazard'.
    A turn that is only a person name is not compared with hazard prototypes.
    """
    cleaned = " ".join((text or "").split())
    if len(cleaned) < 8 or _person_name_only(cleaned):
        return "none", None
    if _load_failed:
        return "ask", "Hazard model unavailable"
    try:
        vector = _embed([cleaned])[0]
        bank = _prototypes()
    except EmbedderUnavailable:
        return "ask", "Hazard model unavailable"
    except Exception:
        return "ask", "Hazard model unavailable"
    ranked: list[tuple[float, float, str]] = []
    for concept, (hazard, routine) in bank.items():
        hazard_score = _max_cosine(vector, hazard)
        routine_score = _max_cosine(vector, routine)
        ranked.append((hazard_score, hazard_score - routine_score, concept))
    hazard_score, margin, concept = max(ranked)
    if hazard_score >= DEFINITE_COSINE and margin >= DEFINITE_MARGIN:
        return "definite", _LABELS[concept]
    if hazard_score >= ASK_COSINE and margin >= ASK_MARGIN:
        return "ask", _LABELS[concept]
    return "none", None


def _embed(lines: list[str]) -> np.ndarray:
    vectors = list(_embedder().embed(lines))
    return np.vstack([np.asarray(item, dtype=np.float32) for item in vectors])


def _weights_present(cache: str | None) -> bool:
    from fastembed.common.utils import define_cache_dir

    root = Path(define_cache_dir(cache))
    folder = root / "models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2"
    if not folder.exists():
        return False
    return any(folder.rglob("model.onnx")) or any(folder.rglob("model_optimized.onnx"))


def _embedder():
    global _model, _load_failed
    if _model is not None:
        return _model
    if _load_failed:
        raise EmbedderUnavailable("hazard embedder failed to load")
    cache = os.environ.get("FASTEMBED_CACHE_PATH")
    offline = os.environ.get("HF_HUB_OFFLINE") == "1" or _weights_present(cache)
    try:
        from fastembed import TextEmbedding

        kwargs: dict = {"local_files_only": True} if offline else {}
        if cache:
            kwargs["cache_dir"] = cache
        _model = TextEmbedding(MODEL_NAME, **kwargs)
    except Exception as exc:
        _load_failed = True
        _model = None
        raise EmbedderUnavailable("hazard embedder failed to load") from exc
    return _model


def _prototypes() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    global _bank
    if _bank is None:
        _bank = {
            concept: (_embed(_HAZARD[concept]), _embed(_ROUTINE[concept]))
            for concept in _LABELS
        }
    return _bank


def _max_cosine(vector: np.ndarray, matrix: np.ndarray) -> float:
    denom = float(np.linalg.norm(vector)) + 1e-9
    norms = np.linalg.norm(matrix, axis=1) + 1e-9
    scores = (matrix @ vector) / (norms * denom)
    return float(scores.max())
