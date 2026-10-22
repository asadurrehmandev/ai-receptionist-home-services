"""Offline zero-shot second opinion for unseen hazard wording.

MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33 runs on ONNX Runtime.
The score is the max entailment of the caller turn against a short label
set whose parent label is "an immediate safety risk to people or property."
Rules still decide past, hypothetical, and plain jobs before this runs.
A missing model is remembered and is not retried.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

MODEL_REPO = "MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33"
HIGH_ENTAILMENT = 0.85
MED_ENTAILMENT = 0.62

# Parent label first. The others unpack that same risk for a small NLI model.
_HYPOTHESES: tuple[tuple[str, str], ...] = (
    ("risk", "This example is an immediate safety risk to people or property."),
    ("sick", "This example is about a person who is dizzy, faint, confused, or hard to wake."),
    ("baby", "This example is about a baby or infant in a home with no heat or extreme cold."),
    ("flood", "This example is about flooding, a burst pipe, or water destroying the building."),
    ("gas", "This example is about a gas smell, a fuel leak, or a hissing gas line."),
    ("garage", "This example is about an engine or generator running inside a garage."),
    ("fire", "This example is about fire, smoke, or sparks."),
)
_LABELS = {
    "risk": "Immediate safety risk",
    "sick": "Caller symptom",
    "baby": "Unsafe indoor temperature",
    "flood": "Active water",
    "gas": "Gas",
    "garage": "Carbon monoxide",
    "fire": "Electrical hazard",
}

_session = None
_tokenizer = None
_load_failed = False
_last_ms: float | None = None


class NliUnavailable(RuntimeError):
    """The zero-shot weights could not be loaded. Callers must fail closed."""


def model_dir() -> Path:
    override = os.environ.get("NLI_MODEL_DIR")
    if override:
        return Path(override)
    cache = os.environ.get("FASTEMBED_CACHE_PATH")
    if cache:
        return Path(cache) / "nli"
    return Path(__file__).resolve().parents[3] / "models" / "nli"


def nli_ready() -> bool:
    """True only after the local ONNX weights have loaded."""
    if _load_failed:
        return False
    if _session is not None:
        return True
    try:
        _runtime()
    except NliUnavailable:
        return False
    return _session is not None


def last_latency_ms() -> float | None:
    return _last_ms


def nli_opinion(text: str) -> tuple[str, str | None]:
    """Return ('definite'|'ask'|'none'|'unavailable', label).

    High entailment can page. Medium entailment only asks. A missing model
    does not invent a clearance.
    """
    cleaned = " ".join((text or "").split())
    if len(cleaned) < 8:
        return "none", None
    if _load_failed:
        return "unavailable", None
    try:
        scores = _entailment(cleaned)
    except NliUnavailable:
        return "unavailable", None
    except Exception:
        return "unavailable", None
    name, score = max(scores.items(), key=lambda item: item[1])
    if score >= HIGH_ENTAILMENT:
        return "definite", _LABELS[name]
    if score >= MED_ENTAILMENT:
        return "ask", _LABELS[name]
    return "none", None


def _entailment(premise: str) -> dict[str, float]:
    import time

    global _last_ms
    session, tokenizer = _runtime()
    encoded = [tokenizer.encode(premise, hypothesis) for _name, hypothesis in _HYPOTHESES]
    width = min(160, max(len(item.ids) for item in encoded))
    rows = len(encoded)
    ids = np.zeros((rows, width), dtype=np.int64)
    mask = np.zeros((rows, width), dtype=np.int64)
    for index, item in enumerate(encoded):
        take = min(len(item.ids), width)
        ids[index, :take] = item.ids[:take]
        mask[index, :take] = item.attention_mask[:take]
    started = time.perf_counter()
    logits = session.run(None, {"input_ids": ids, "attention_mask": mask})[0]
    _last_ms = (time.perf_counter() - started) * 1000
    shifted = logits - logits.max(axis=1, keepdims=True)
    probs = np.exp(shifted)
    probs /= probs.sum(axis=1, keepdims=True)
    return {name: float(probs[index, 0]) for index, (name, _hypothesis) in enumerate(_HYPOTHESES)}


def _runtime():
    global _session, _tokenizer, _load_failed
    if _session is not None and _tokenizer is not None:
        return _session, _tokenizer
    if _load_failed:
        raise NliUnavailable("nli model failed to load")
    root = model_dir()
    onnx = root / "onnx" / "model_quantized.onnx"
    tokenizer_path = root / "tokenizer.json"
    if not onnx.exists() or not tokenizer_path.exists():
        _load_failed = True
        raise NliUnavailable("nli weights are not on disk")
    try:
        import onnxruntime as ort
        from tokenizers import Tokenizer

        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        _tokenizer = Tokenizer.from_file(str(tokenizer_path))
        _tokenizer.enable_truncation(max_length=160)
        _session = ort.InferenceSession(str(onnx), sess_options=options, providers=["CPUExecutionProvider"])
    except Exception as exc:
        _load_failed = True
        _session = None
        _tokenizer = None
        raise NliUnavailable("nli model failed to load") from exc
    return _session, _tokenizer
