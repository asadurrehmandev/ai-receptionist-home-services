"""Learned hazard and service heads on a multilingual MiniLM embedding.

The head is a multinomial logistic regression. It is the base screen.
Hand rules may raise its level. They do not lower it. If the weights or the
embedder are missing, callers fall back to the rules alone.

The vector is the sentence embedding plus a hashed character-and-word
sketch. The sketch is what lets typos and romanized wording move the
score when the sentence model keeps those lines far from English.

Labels are emergency, ask_safety, routine, and other. A second head on the
same vector picks a service for ordinary booking.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

WORD_DIM = 1024
CHAR_DIM = 1024
WORD_SCALE = 2.2
CHAR_SCALE = 0.7

HAZARD_LABELS = ("emergency", "ask_safety", "routine", "other")
SERVICE_LABELS = (
    "emergency",
    "drain",
    "water_heater",
    "toilet",
    "faucet",
    "disposal",
    "ac",
    "heat",
    "leak",
    "sewer",
    "caulk",
    "fireplace",
    "shower_head",
    "dryer_gas",
    "grill_gas",
    "washer",
    "filter",
    "lighting",
    "other",
)
SERVICE_ISSUE = {
    "drain": "Clogged drain",
    "water_heater": "Water heater",
    "toilet": "Toilet",
    "faucet": "Faucet",
    "disposal": "Garbage disposal",
    "ac": "AC repair",
    "heat": "Heating repair",
    "leak": "Leak",
    "sewer": "Sewer line",
    "caulk": "Caulking",
    "fireplace": "Gas fireplace service",
    "shower_head": "Shower head",
    "dryer_gas": "Dryer gas line",
    "grill_gas": "Gas grill line",
    "washer": "Washer",
    "filter": "Water filter",
    "lighting": "Lighting",
}

# Asymmetric: a high emergency probability pages. Anything uncertain that still
# carries hazard mass asks. A confident routine or other line can be booked.
# The word head uses a lower page bar. It only fires when the spelling itself
# is an emergency, which is how romanized and typo lines page without pulling
# a mild faucet leak over the line.
EMERGENCY_MIN = 0.86
WORD_EMERGENCY_MIN = 0.60
ROUTINE_MIN = 0.46
OTHER_MIN = 0.42
ASK_MASS = 0.33

_WEIGHTS: dict | None | bool = None


def decide(probs: np.ndarray) -> str:
    """Map class probabilities to emergency, ask_safety, routine, or other.

    Page only on a confident emergency that beats routine. A strong ask, or
    an emergency that leads while routine is weak, asks instead of booking.
    A competitive routine probability stays bookable.
    """
    p_em, p_ask, p_routine, p_other = (float(probs[0]), float(probs[1]), float(probs[2]), float(probs[3]))
    if p_em >= EMERGENCY_MIN and p_em >= p_ask and (p_em - p_routine) >= 0.18:
        return "emergency"
    if p_ask >= 0.66 and p_ask >= p_routine and p_ask >= p_em:
        return "ask_safety"
    if p_em >= 0.50 and p_routine < 0.05 and p_em >= p_ask:
        return "ask_safety"
    if p_routine >= p_other:
        return "routine"
    return "other"


def word_pages(probs: np.ndarray) -> bool:
    """True when the spelling head is sure this is an emergency."""
    p_em, p_ask, p_routine = (float(probs[0]), float(probs[1]), float(probs[2]))
    return p_em >= WORD_EMERGENCY_MIN and p_em >= p_ask and (p_em - p_routine) >= 0.18


def spelling_raises(full: np.ndarray, spelling: np.ndarray | None) -> bool:
    """Let the spelling head page only in the embedding's 'other' region.

    Romanized lines sit near names, so P(other) competes with P(routine).
    An ordinary English job, even one that mentions gas or an alarm, has
    P(routine) clearly ahead of P(other) and is left to the embedding head.
    """
    if spelling is None or not word_pages(spelling):
        return False
    p_routine = float(full[2])
    p_other = float(full[3])
    return p_other >= 0.10 and p_other + 0.02 >= p_routine


def _path() -> Path:
    return Path(__file__).resolve().parent / "data" / "hazard_head.npz"


def _weights() -> dict | None:
    global _WEIGHTS
    if _WEIGHTS is False:
        return None
    if isinstance(_WEIGHTS, dict):
        return _WEIGHTS
    path = _path()
    if not path.exists():
        _WEIGHTS = False
        return None
    loaded = np.load(path)
    _WEIGHTS = {
        "hazard_W": np.asarray(loaded["hazard_W"], dtype=np.float32),
        "hazard_b": np.asarray(loaded["hazard_b"], dtype=np.float32),
        "service_W": np.asarray(loaded["service_W"], dtype=np.float32),
        "service_b": np.asarray(loaded["service_b"], dtype=np.float32),
    }
    if "word_W" in loaded:
        _WEIGHTS["word_W"] = np.asarray(loaded["word_W"], dtype=np.float32)
        _WEIGHTS["word_b"] = np.asarray(loaded["word_b"], dtype=np.float32)
    return _WEIGHTS


def head_ready() -> bool:
    if _weights() is None:
        return False
    from app.agent.hazard_semantic import semantic_ready

    return semantic_ready()


def _bucket(token: str, dim: int) -> int:
    """FNV-1a. Stable across processes, unlike Python's salted hash."""
    h = 2166136261
    for ch in token:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h % dim


def _sketch(texts: list[str]) -> np.ndarray:
    """Word unigrams and bigrams, plus character grams, on separate scales.

    Each channel is normalized on its own so a long character stream cannot
    drown the words. Words are what separate 'gas boo' from a person's name
    when the sentence embedding keeps them close.
    """
    words = np.zeros((len(texts), WORD_DIM), dtype=np.float32)
    chars = np.zeros((len(texts), CHAR_DIM), dtype=np.float32)
    for i, text in enumerate(texts):
        folded = " ".join((text or "").lower().split())
        if not folded:
            continue
        tokens = [tok for tok in folded.split() if len(tok) >= 2]
        for tok in tokens:
            words[i, _bucket("w:" + tok, WORD_DIM)] += 1.0
        for left, right in zip(tokens, tokens[1:]):
            words[i, _bucket("b:" + left + "_" + right, WORD_DIM)] += 1.4
        padded = f"^{folded}$"
        for n in (3, 4):
            if len(padded) < n:
                continue
            for j in range(len(padded) - n + 1):
                chars[i, _bucket(padded[j : j + n], CHAR_DIM)] += 1.0
        word_norm = float(np.linalg.norm(words[i])) + 1e-9
        char_norm = float(np.linalg.norm(chars[i])) + 1e-9
        words[i] /= word_norm
        chars[i] /= char_norm
    return np.concatenate([words * WORD_SCALE, chars * CHAR_SCALE], axis=1)


def featurize(texts: list[str]) -> np.ndarray | None:
    """Embedding plus the hashed sketch. None when the embedder cannot run."""
    cleaned = [" ".join((text or "").split()) for text in texts]
    if not any(cleaned):
        return None
    from app.agent.hazard_semantic import _embed, semantic_ready

    if not semantic_ready():
        return None
    try:
        emb = np.asarray(_embed(cleaned), dtype=np.float32)
    except Exception:
        return None
    norms = np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9
    emb = emb / norms
    return np.concatenate([emb, _sketch(cleaned)], axis=1)


def _vector(text: str) -> np.ndarray | None:
    cleaned = " ".join((text or "").split())
    if not cleaned or _weights() is None:
        return None
    matrix = featurize([cleaned])
    if matrix is None:
        return None
    return matrix[0]


def _softmax(row: np.ndarray) -> np.ndarray:
    shifted = row - float(row.max())
    exp = np.exp(shifted)
    return exp / float(exp.sum())


def hazard_probs(text: str) -> np.ndarray | None:
    weights = _weights()
    vector = _vector(text)
    if weights is None or vector is None:
        return None
    return _softmax(weights["hazard_W"] @ vector + weights["hazard_b"])


def word_probs(text: str) -> np.ndarray | None:
    """Spelling-head probabilities. None when that head was not trained."""
    weights = _weights()
    vector = _vector(text)
    if weights is None or vector is None or "word_W" not in weights:
        return None
    sketch = vector[384:]
    if sketch.shape[0] != weights["word_W"].shape[1]:
        return None
    return _softmax(weights["word_W"] @ sketch + weights["word_b"])


def confident_routine(text: str) -> bool:
    """True when the head would book this line and is not sitting on a hazard."""
    probs = hazard_probs(text)
    if probs is None:
        return False
    return decide(probs) in {"routine", "other"} and float(probs[0]) < 0.22 and float(probs[1]) < 0.28


def head_level(text: str) -> tuple[str, str | None] | None:
    """The head's own level. None means it could not run, not that the line is safe."""
    target = text or ""
    try:
        from app.agent.hazard import _instruction_only, prepare

        folded = prepare(target)
        if _instruction_only(folded):
            return "none", None
    except Exception:
        target = text or ""
    vector = _vector(target)
    weights = _weights()
    if vector is None or weights is None:
        return None
    if vector.shape[0] != weights["hazard_W"].shape[1]:
        return None
    probs = _softmax(weights["hazard_W"] @ vector + weights["hazard_b"])
    label = decide(probs)
    spelling = None
    if "word_W" in weights and weights["word_W"].shape[1] == vector.shape[0] - 384:
        spelling = _softmax(weights["word_W"] @ vector[384:] + weights["word_b"])
    if label == "emergency" or spelling_raises(probs, spelling):
        return "definite", _family(text)
    if label == "ask_safety":
        return "ask", "Uncertain hazard"
    return "none", None


def _family(text: str) -> str:
    """A display label after the head has already decided to page."""
    folded = (text or "").lower()
    tokens = set(folded.replace(",", " ").split())
    if tokens & {"co", "monoxide", "monoxido", "chakkar", "dizzy", "headache", "dard"} or any(
        word in folded for word in ("monox", "carbon", "dolor de cabeza")
    ):
        return "Carbon monoxide"
    if any(word in folded for word in ("spark", "chispa", "outlet", "breaker", "enchufe", "cord", "smoke", "humo")):
        if any(word in folded for word in ("water", "agua", "pani", "steam", "vapor")):
            return "Electrical hazard"
    if any(word in folded for word in ("gas", "propane", "boo", "olor a gas", "huele")):
        return "Gas"
    if any(word in folded for word in ("steam", "vapor", "burn", "scald", "jal ")) or "quem" in folded:
        return "Active water"
    if any(word in folded for word in ("water", "agua", "pani", "flood", "burst", "pipe")):
        return "Active water"
    return "Hazard"


def route_service(text: str) -> tuple[str, float] | None:
    """Service id and probability for an ordinary job. None when the head is down."""
    weights = _weights()
    vector = _vector(text)
    if weights is None or vector is None:
        return None
    probs = _softmax(weights["service_W"] @ vector + weights["service_b"])
    index = int(probs.argmax())
    return SERVICE_LABELS[index], float(probs[index])


def route_issue(text: str) -> str | None:
    """Issue label when the service head is confident and the line is not a hazard."""
    routed = route_service(text)
    if routed is None:
        return None
    service, score = routed
    if service in {"other", "emergency"} or score < 0.42:
        return None
    hazard = hazard_probs(text)
    if hazard is not None and decide(hazard) in {"emergency", "ask_safety"}:
        return None
    return SERVICE_ISSUE.get(service)
