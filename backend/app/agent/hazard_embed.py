"""Multilingual hazard prototypes, scored by character-trigram cosine similarity.

This is the second opinion next to the concept rules. It is a local embedding,
not a downloaded NLI checkpoint. Prototypes are short hazard descriptions in
several languages. A caller sentence is urgent when it sits closer to a hazard
prototype than to a routine one. Past-tense wording is damped unless a
present-tense hazard verb is also there.
"""

from __future__ import annotations

import math
import re
import unicodedata

_PAST = re.compile(
    r"\b(last|ago|yesterday|previously|used to|in may|in june|during the|"
    r"two weeks|months ago|years ago|was fixed|already fixed)\b",
    re.I,
)
_PRESENT = re.compile(
    r"\b(is|are|am|smell|smelling|hissing|pouring|gushing|spraying|spewing|"
    r"beeping|sparking|smoking|won't|wont|cannot|can't|coming|right now|ahora)\b",
    re.I,
)

# Short prototypes. Not caller transcripts.
_PROTOTYPES: dict[str, tuple[str, ...]] = {
    "gas": (
        "i smell gas in the house",
        "there is a gas odor by the stove",
        "the gas line is hissing",
        "huele a gas en la casa",
        "olor a gas ahora",
        "ca sent le gaz",
        "odeur de gaz dans la cuisine",
        "cheiro de gas na cozinha",
        "vazamento de gas",
        "mui gas trong nha",
        "amoy ng gas sa bahay",
        "gas leak right now",
    ),
    "co": (
        "the alarm is beeping and people feel sick",
        "carbon monoxide detector sounding and we are dizzy",
        "detector sonando y estamos mareados",
        "alarme de monoxide et mal de tete",
        "detector apitando e nauseas",
        "kids are vomiting and the hall alarm will not stop",
    ),
    "water": (
        "water is spraying and will not stop",
        "the basement is flooding right now",
        "sewage is coming up out of the drain",
        "se esta inundando la casa",
        "agua saliendo sin parar",
        "la maison est inondee",
        "esta alagando a casa",
        "tubo estourou e a agua nao para",
        "nha dang ngap nuoc",
        "sumabog ang tubo at bumabaha",
        "washer hose is spraying across the room",
    ),
    "electrical": (
        "the outlet is sparking",
        "smoke from the breaker panel",
        "the wall switch is hot and smells like burning",
        "burning plastic smell from the plug",
        "chispas en el enchufe",
        "prise qui fume",
        "tomada com cheiro de queimado",
    ),
    "comfort": (
        "no heat and a baby is in the house",
        "the furnace is not working and it is freezing",
        "the heat will not come on and an elderly person is here",
        "air conditioner stopped and someone is on oxygen",
        "it is very cold and the heater broke",
        "no hay calor y hay un bebe",
        "pas de chauffage et un nourrisson",
        "sem aquecimento e uma crianca",
    ),
    "none": (
        "how much is the emergency visit fee",
        "quote to convert a stove to gas",
        "the car ran out of gas",
        "a slow drip from the faucet",
        "schedule a drain cleaning",
        "the old leak left a dry stain",
        "install a gas line when you have time",
        "price for a sump pump",
        "not an emergency just a toilet that runs",
        "my wallet is the problem",
    ),
}

def _fold(text: str) -> str:
    cleaned = (text or "").lower().replace("’", "'")
    stripped = "".join(ch for ch in unicodedata.normalize("NFKD", cleaned) if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", stripped).strip()


def _vector(text: str) -> tuple[dict[str, float], float]:
    folded = _fold(text)
    counts: dict[str, float] = {}
    padded = f" {folded} "
    for index in range(max(len(padded) - 2, 0)):
        gram = padded[index : index + 3]
        counts[gram] = counts.get(gram, 0.0) + 1.0
    for word in folded.split():
        if len(word) < 2:
            continue
        counts[f"w:{word}"] = counts.get(f"w:{word}", 0.0) + 3.0
    norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
    return counts, norm


def _cosine(left: tuple[dict[str, float], float], right: tuple[dict[str, float], float]) -> float:
    a, a_norm = left
    b, b_norm = right
    if len(a) > len(b):
        a, b = b, a
        a_norm, b_norm = b_norm, a_norm
    dot = sum(value * b.get(key, 0.0) for key, value in a.items())
    return dot / (a_norm * b_norm)


_LINE_CACHE: dict[str, list[tuple[dict[str, float], float]]] = {}


def _prototypes(label: str) -> list[tuple[dict[str, float], float]]:
    bucket = _LINE_CACHE.get(label)
    if bucket is None:
        bucket = [_vector(line) for line in _PROTOTYPES[label]]
        _LINE_CACHE[label] = bucket
    return bucket


def embed_hazard(text: str) -> tuple[str, str | None]:
    """Return ('definite'|'ask'|'none', label)."""
    folded = _fold(text)
    if len(folded) < 8:
        return "none", None
    current = _vector(folded)
    best_label = "none"
    best_score = 0.0
    none_score = 0.0
    for label in _PROTOTYPES:
        score = max(_cosine(current, proto) for proto in _prototypes(label))
        if label == "none":
            none_score = score
            continue
        if score > best_score:
            best_score = score
            best_label = label
    if _PAST.search(folded) and not _PRESENT.search(folded):
        best_score *= 0.45
    names = {
        "gas": "Gas",
        "co": "Carbon monoxide",
        "water": "Active water",
        "electrical": "Electrical hazard",
        "comfort": "Unsafe indoor temperature",
    }
    if best_score >= 0.62 and best_score >= none_score + 0.08:
        return "definite", names[best_label]
    if best_score >= 0.48 and best_score >= none_score + 0.03:
        return "ask", names[best_label]
    return "none", None
