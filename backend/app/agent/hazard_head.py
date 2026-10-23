"""Learned hazard and service heads.

The head is a multinomial logistic regression on a multilingual sentence
embedding. It is the base screen and it runs on every caller turn. Hand
rules may raise its level. A routine clearance may block a page. A word
list never skips the embedding.

Labels are emergency, ask_safety, routine, and other. A second head on the
same vector picks a service for ordinary booking.

Thresholds are chosen on a validation split and stored with the weights.
A high emergency score pages. A middle band asks the safety question.
A low score proceeds.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

WORD_DIM = 1024
CHAR_DIM = 1024
WORD_SCALE = 2.2
CHAR_SCALE = 0.7
COS_SCALE = 4.0
# multilingual-e5-large is 1024-d and about 2.2 GB on disk. With MiniLM and
# DeBERTa also loaded, process RSS is about 2.6 GB. fastembed 0.6.1 does not
# ship multilingual-e5-small. A MiniLM logistic head trained on the same
# corpus reached 0.72 held-out emergency recall, under the 0.90 bar, so the
# desk keeps e5-large. The word list does not skip this embedding.
EMBED_MODEL = "intfloat/multilingual-e5-large"

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

# Defaults until a trained file replaces them. The file is the source of truth.
PAGE_MIN = 0.80
ASK_MIN = 0.45
PAGE_MARGIN = 0.15
ROUTINE_LOCK = 0.70

_WEIGHTS: dict | None | bool = None
_MODEL: object | None | bool = None


def decide(probs: np.ndarray) -> str:
    """Map class probabilities to emergency, ask_safety, routine, or other.

    High emergency probability pages. A middle band asks. A confident routine
    score proceeds even if a little hazard mass remains.
    """
    p_em, p_ask, p_routine, p_other = (float(probs[0]), float(probs[1]), float(probs[2]), float(probs[3]))
    if p_em >= PAGE_MIN and p_em >= p_ask and (p_em - p_routine) >= PAGE_MARGIN:
        return "emergency"
    if p_routine >= ROUTINE_LOCK and p_routine >= p_em and p_routine >= p_ask:
        return "routine"
    if (p_em >= ASK_MIN and p_em >= p_routine) or (p_ask >= ASK_MIN and p_ask >= p_routine and p_ask >= p_em):
        return "ask_safety"
    if p_routine >= p_other:
        return "routine"
    return "other"


def _path() -> Path:
    return Path(__file__).resolve().parent / "data" / "hazard_head.npz"


def _apply_thresholds(loaded: np.lib.npyio.NpzFile) -> None:
    global PAGE_MIN, ASK_MIN, PAGE_MARGIN, ROUTINE_LOCK
    if "page_min" in loaded:
        PAGE_MIN = float(loaded["page_min"])
    if "ask_min" in loaded:
        ASK_MIN = float(loaded["ask_min"])
    if "page_margin" in loaded:
        PAGE_MARGIN = float(loaded["page_margin"])
    if "routine_lock" in loaded:
        ROUTINE_LOCK = float(loaded["routine_lock"])


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
    _apply_thresholds(loaded)
    _WEIGHTS = {
        "hazard_W": np.asarray(loaded["hazard_W"], dtype=np.float32),
        "hazard_b": np.asarray(loaded["hazard_b"], dtype=np.float32),
        "service_W": np.asarray(loaded["service_W"], dtype=np.float32),
        "service_b": np.asarray(loaded["service_b"], dtype=np.float32),
        "centroids": np.asarray(loaded["centroids"], dtype=np.float32) if "centroids" in loaded else None,
        "proto_emergency": np.asarray(loaded["proto_emergency"]) if "proto_emergency" in loaded else None,
        "page_t": float(loaded["page_t"]) if "page_t" in loaded else None,
        "ask_t": float(loaded["ask_t"]) if "ask_t" in loaded else None,
    }
    return _WEIGHTS


def _cache_dir() -> str | None:
    return os.environ.get("FASTEMBED_CACHE_PATH") or None


def _e5():
    """The multilingual embedder. None when the weights are not on disk.

    The MiniLM head reuses the prototype embedder so the process does not
    load a second copy of the same checkpoint.
    """
    global _MODEL
    if _MODEL is False:
        return None
    if _MODEL is not None:
        return _MODEL
    if EMBED_MODEL == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2":
        try:
            from app.agent.hazard_semantic import _embedder

            _MODEL = _embedder()
            return _MODEL
        except Exception:
            _MODEL = False
            return None
    try:
        from fastembed import TextEmbedding
    except Exception:
        _MODEL = False
        return None
    kwargs = {"cache_dir": _cache_dir()} if _cache_dir() else {}
    try:
        _MODEL = TextEmbedding(EMBED_MODEL, local_files_only=True, **kwargs)
    except Exception:
        if os.environ.get("HF_HUB_OFFLINE") == "1":
            _MODEL = False
            return None
        try:
            _MODEL = TextEmbedding(EMBED_MODEL, **kwargs)
        except Exception:
            _MODEL = False
            return None
    return _MODEL


def head_ready() -> bool:
    """True when the checkpoint and the weights share one vector size."""
    weights = _weights()
    if weights is None or _e5() is None:
        return False
    sample = embed_texts(["ready"])
    if sample is None:
        return False
    return int(sample.shape[1]) == int(weights["hazard_W"].shape[1])


def _bucket(token: str, dim: int) -> int:
    """FNV-1a. Stable across processes, unlike Python's salted hash."""
    h = 2166136261
    for ch in token:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h % dim


def _sketch(texts: list[str]) -> np.ndarray:
    """Word unigrams and bigrams, plus character grams, on separate scales."""
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


def embed_texts(texts: list[str]) -> np.ndarray | None:
    """L2-normalized embeddings. e5 models require a query prefix. MiniLM does not."""
    model = _e5()
    if model is None:
        return None
    cleaned = [" ".join((text or "").split()) for text in texts]
    if "e5" in EMBED_MODEL:
        prefixed = [f"query: {text}" if text else "query: " for text in cleaned]
    else:
        prefixed = cleaned
    try:
        rows = [np.asarray(vector, dtype=np.float32) for vector in model.embed(prefixed)]
    except Exception:
        return None
    if not rows:
        return None
    matrix = np.vstack(rows)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9
    return matrix


def compose_features(
    embeddings: np.ndarray,
    texts: list[str],
    centroids: np.ndarray | None = None,
    proto_emergency: np.ndarray | None = None,
) -> np.ndarray:
    """The e5 embedding. Extra channels were drowning the direction that separates hazards."""
    del texts, centroids, proto_emergency
    return np.asarray(embeddings, dtype=np.float32)


def featurize(texts: list[str]) -> np.ndarray | None:
    """Full vector. None when the embedder or the centroids cannot run."""
    cleaned = [" ".join((text or "").split()) for text in texts]
    if not any(cleaned):
        return None
    if _weights() is None:
        return None
    return embed_texts(cleaned)


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
    if vector.shape[0] != weights["hazard_W"].shape[1]:
        return None
    return _softmax(weights["hazard_W"] @ vector + weights["hazard_b"])


def confident_routine(text: str) -> bool:
    """True when the head would book this line and is not sitting on a hazard."""
    probs = hazard_probs(text)
    if probs is None:
        return False
    return decide(probs) in {"routine", "other"} and float(probs[0]) < 0.22 and float(probs[1]) < 0.28


def head_level(text: str) -> tuple[str, str | None] | None:
    """The head's own level. None means it could not run, not that the line is safe.

    Every non-empty turn is embedded. A word list does not skip this call.
    """
    target = text or ""
    probs = hazard_probs(target)
    if probs is None:
        return None
    label = decide(probs)
    if label == "emergency":
        return "definite", _family(text)
    if label == "ask_safety":
        return "ask", "Uncertain hazard"
    return "none", None


def _family(text: str) -> str:
    """A display label after the head has already decided to page."""
    folded = (text or "").lower()
    if any(word in folded for word in ("monox", "carbon", "co alarm", "co detector", "dolor de cabeza", "dard")):
        return "Carbon monoxide"
    if any(word in folded for word in ("spark", "chispa", "smoke", "humo", "dhuan", "faísca", "faisca", "شرار")):
        return "Electrical hazard"
    if any(word in folded for word in ("sewage", "sewer", "aguas negras", "esgoto")):
        return "Sewage"
    if any(word in folded for word in ("heat", "heater", "furnace", "cooling", "calor", "aquecimento", "हीटर", "ہیٹر")):
        if any(word in folded for word in ("baby", "infant", "elderly", "abuela", "dadi", "lola", "جدة", "جدتي")):
            return "Unsafe indoor temperature"
    if any(word in folded for word in ("gas", "propane", "boo", "olor a gas", "huele", "gás", "غاز")):
        return "Gas"
    if any(word in folded for word in ("water", "agua", "pani", "paani", "flood", "burst", "pipe", "água")):
        return "Active water"
    return "Hazard"


def route_service(text: str) -> tuple[str, float] | None:
    """Service id and probability for an ordinary job. None when the head is down."""
    weights = _weights()
    vector = _vector(text)
    if weights is None or vector is None:
        return None
    if vector.shape[0] != weights["service_W"].shape[1]:
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
