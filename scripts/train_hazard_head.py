"""Train the hazard and service heads. Does not read QA reports.

The round-13 held-out file is scored after the threshold is locked on a
validation split of the synthetic corpus. Those sentences are not trained on.

    FASTEMBED_CACHE_PATH=/workspace/models HF_HUB_OFFLINE=1 PYTHONPATH=backend \\
        python3 scripts/train_hazard_head.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.agent.hazard_head import (  # noqa: E402
    HAZARD_LABELS,
    SERVICE_LABELS,
    compose_features,
    decide,
    embed_texts,
)
from hazard_corpus import build  # noqa: E402

# Shipped e5-large weights used this seed. A MiniLM trial on 20261024 was discarded.
SEED = 20261023
OUT = ROOT / "backend" / "app" / "agent" / "data" / "hazard_head.npz"
METRICS = ROOT / "evals" / "hazard_train_metrics.json"


def _frozen_texts() -> set[str]:
    banned: set[str] = set()
    from evals.fresh_set import FRESH
    from evals.heldout_set import HELDOUT as OLD
    from evals.round7_set import ROUND7
    from evals.round8_set import ROUND8
    from evals.round9_set import ROUND9
    from evals.round11_set import ROUND11
    from evals.round13_heldout_set import HELDOUT as ROUND13
    from evals.round14_heldout_set import HELDOUT as ROUND14
    from evals.unseen_set import UNSEEN

    for pool in (FRESH, OLD, ROUND7, ROUND8, ROUND9, ROUND11, UNSEEN):
        for row in pool:
            banned.add(" ".join(row[-1].split()).casefold())
    for pool in (ROUND13, ROUND14):
        for _label, _family, _language, text in pool:
            banned.add(" ".join(text.split()).casefold())
    test = ROOT / "backend" / "tests" / "test_round13.py"
    if test.exists():
        # Quoted lines in the new tests stay out of the fit.
        import re

        for match in re.findall(r'"([^"\n]{12,})"', test.read_text()):
            banned.add(" ".join(match.split()).casefold())
    return banned


def _fit(
    features: np.ndarray,
    y: np.ndarray,
    n_classes: int,
    rng: np.random.Generator,
    sample_w: np.ndarray | None = None,
    l2: float = 3e-4,
    epochs: int = 220,
) -> tuple[np.ndarray, np.ndarray]:
    n, dim = features.shape
    weights = rng.normal(0.0, 0.01, size=(n_classes, dim))
    bias = np.zeros(n_classes, dtype=np.float64)
    eye = np.eye(n_classes)
    if sample_w is None:
        counts = np.bincount(y, minlength=n_classes).astype(np.float64)
        class_w = np.sqrt(n / (n_classes * np.maximum(counts, 1.0)))
        class_w = class_w / float(class_w.mean())
        sample_w = class_w[y]
    lr = 3.0
    best = (weights.copy(), bias.copy(), -1.0)
    for epoch in range(epochs):
        logits = features @ weights.T + bias
        logits -= logits.max(axis=1, keepdims=True)
        exp = np.exp(logits)
        probs = exp / exp.sum(axis=1, keepdims=True)
        residual = (probs - eye[y]) * sample_w[:, None]
        grad_w = residual.T @ features / n + l2 * weights
        grad_b = residual.sum(axis=0) / n
        weights -= lr * grad_w
        bias -= lr * grad_b
        pred = probs.argmax(axis=1)
        recalls = []
        for cls in range(n_classes):
            mask = y == cls
            if mask.any():
                recalls.append(float((pred[mask] == cls).mean()))
        macro = float(np.mean(recalls)) if recalls else 0.0
        if macro > best[2]:
            best = (weights.copy(), bias.copy(), macro)
        if epoch in {0, 40, 120, epochs - 1}:
            print(f"  epoch {epoch:3d} acc {float((pred == y).mean()):.3f} macro {macro:.3f}", flush=True)
    return best[0].astype(np.float32), best[1].astype(np.float32)


def _probs(matrix: np.ndarray, weight: np.ndarray, bias: np.ndarray) -> np.ndarray:
    logits = matrix @ weight.T + bias
    logits -= logits.max(axis=1, keepdims=True)
    exp = np.exp(logits)
    return exp / exp.sum(axis=1, keepdims=True)


def _apply(page_min: float, ask_min: float, margin: float, routine_lock: float) -> None:
    import app.agent.hazard_head as head

    head.PAGE_MIN = page_min
    head.ASK_MIN = ask_min
    head.PAGE_MARGIN = margin
    head.ROUTINE_LOCK = routine_lock


def _score(probs: np.ndarray, labels: list[str]) -> dict:
    pred = [decide(row) for row in probs]
    counts = {label: {"n": 0, "hit": 0} for label in HAZARD_LABELS}
    false_pages = 0
    routine_n = 0
    routine_ask = 0
    non_emergency = 0
    for guess, truth in zip(pred, labels):
        if truth not in counts:
            truth = "routine" if truth == "advice" else truth
        counts[truth]["n"] += 1
        if guess == truth:
            counts[truth]["hit"] += 1
        if truth != "emergency" and guess == "emergency":
            false_pages += 1
            non_emergency += 1
        elif truth != "emergency":
            non_emergency += 1
        if truth == "routine":
            routine_n += 1
            if guess == "ask_safety":
                routine_ask += 1
    emergencies = counts["emergency"]["n"]
    summary = {}
    for label, item in counts.items():
        n = item["n"]
        summary[label] = {"n": n, "hit": item["hit"], "recall": round(item["hit"] / n, 3) if n else None}
    return {
        "n": len(labels),
        "per_class": summary,
        "emergency_recall": round(counts["emergency"]["hit"] / emergencies, 3) if emergencies else None,
        "false_pages": false_pages,
        "false_page_rate": round(false_pages / non_emergency, 3) if non_emergency else None,
        "routine_to_ask": routine_ask,
        "routine_to_ask_rate": round(routine_ask / routine_n, 3) if routine_n else None,
    }


def _band_probs(margins: np.ndarray, page_t: float, ask_t: float) -> np.ndarray:
    """The same three probability rows hazard_probs returns at runtime."""
    out = np.zeros((len(margins), 4), dtype=np.float32)
    for i, margin in enumerate(margins):
        if margin >= page_t:
            out[i] = (0.95, 0.03, 0.01, 0.01)
        elif margin >= ask_t:
            out[i] = (0.25, 0.65, 0.05, 0.05)
        else:
            out[i] = (0.02, 0.04, 0.90, 0.04)
    return out


def _search_margin(margins: np.ndarray, labels: list[str]) -> tuple[float, float]:
    best = None
    best_key = None
    for page_t in np.linspace(-0.02, 0.12, 29):
        for ask_t in np.linspace(-0.06, float(page_t), 13):
            probs = _band_probs(margins, float(page_t), float(ask_t))
            _apply(0.80, 0.45, 0.15, 0.70)
            scored = _score(probs, labels)
            recall = scored["emergency_recall"] or 0.0
            fpr = scored["false_page_rate"] or 0.0
            ask_rate = scored["routine_to_ask_rate"] or 0.0
            ok = recall >= 0.95 and fpr <= 0.02 and ask_rate <= 0.02
            key = (1 if ok else 0, 1 if fpr <= 0.02 and ask_rate <= 0.05 else 0, recall if fpr <= 0.02 else 0, -fpr, -ask_rate)
            if best_key is None or key > best_key:
                best_key = key
                best = (float(page_t), float(ask_t), scored, ok)
    assert best is not None
    page_t, ask_t, scored, ok = best
    print(
        f"margin page {page_t:.3f} ask {ask_t:.3f} ok {ok} "
        f"recall {scored['emergency_recall']} fpr {scored['false_page_rate']} ask_rate {scored['routine_to_ask_rate']}",
        flush=True,
    )
    return page_t, ask_t


def _search(probs: np.ndarray, labels: list[str]) -> tuple[float, float, float, float, dict]:
    best = None
    best_key = None
    for page_min in (0.35, 0.45, 0.55, 0.65, 0.75, 0.85):
        for ask_min in (0.15, 0.25, 0.35, 0.45, 0.55):
            for margin in (0.02, 0.08, 0.12, 0.18):
                for routine_lock in (0.40, 0.55, 0.70):
                    _apply(page_min, ask_min, margin, routine_lock)
                    scored = _score(probs, labels)
                    recall = scored["emergency_recall"] or 0.0
                    fpr = scored["false_page_rate"] or 0.0
                    ask_rate = scored["routine_to_ask_rate"] or 0.0
                    ok = recall >= 0.95 and fpr <= 0.02 and ask_rate <= 0.02
                    # Stay under the false-page cap, then higher recall. Among those, keep a
                    # middle band so ask_min sits below page_min.
                    gap = 1 if ask_min + 0.05 < page_min else 0
                    key = (
                        1 if fpr <= 0.02 and ask_rate <= 0.05 else 0,
                        round(recall, 2) if fpr <= 0.02 else 0,
                        gap if fpr <= 0.02 and recall >= 0.95 else 0,
                        -fpr,
                        -ask_rate,
                        1 if ok else 0,
                    )
                    if best_key is None or key > best_key:
                        best_key = key
                        best = (page_min, ask_min, margin, routine_lock, scored, ok)
    assert best is not None
    page_min, ask_min, margin, routine_lock, scored, ok = best
    _apply(page_min, ask_min, margin, routine_lock)
    print(
        f"threshold page {page_min} ask {ask_min} margin {margin} routine_lock {routine_lock} "
        f"ok {ok} recall {scored['emergency_recall']} fpr {scored['false_page_rate']}",
        flush=True,
    )
    return page_min, ask_min, margin, routine_lock, scored


def _group_recall(rows: list[tuple], probs: np.ndarray, index: int) -> dict:
    buckets: dict[str, list[bool]] = {}
    for row, prob in zip(rows, probs):
        if row[1] != "emergency":
            continue
        key = row[index]
        buckets.setdefault(key, []).append(decide(prob) == "emergency")
    return {
        key: {"n": len(hits), "hit": sum(hits), "recall": round(sum(hits) / len(hits), 3)}
        for key, hits in sorted(buckets.items())
    }


def _embed_unique(lines: list[str]) -> np.ndarray:
    order: list[str] = []
    index: dict[str, int] = {}
    for line in lines:
        if line not in index:
            index[line] = len(order)
            order.append(line)
    chunks: list[np.ndarray] = []
    batch = 64
    for start in range(0, len(order), batch):
        block = order[start : start + batch]
        matrix = embed_texts(block)
        if matrix is None:
            raise RuntimeError("e5 embedder unavailable")
        chunks.append(matrix)
        done = min(start + batch, len(order))
        if done % 512 == 0 or done == len(order):
            print(f"embedded {done}/{len(order)}", flush=True)
    unique = np.vstack(chunks).astype(np.float32)
    return unique[np.array([index[line] for line in lines], dtype=np.int64)]


def _balance(rows: list, rng: random.Random) -> list:
    """Keep every routine line and a stratified slice of emergencies.

    The raw corpus is mostly emergencies. An unbalanced fit pages everything.
    """
    groups: dict[str, list] = {}
    for row in rows:
        groups.setdefault(row[1], []).append(row)
    routine = groups.get("routine", [])
    asks = groups.get("ask_safety", [])
    other = groups.get("other", [])
    by_family: dict[str, list] = {}
    for row in groups.get("emergency", []):
        by_family.setdefault(row[3], []).append(row)
    cap = max(len(routine), 1) * 2
    per = max(8, cap // max(1, len(by_family)))
    picked: list = []
    for items in by_family.values():
        rng.shuffle(items)
        picked.extend(items[:per])
    rest = routine + asks + other
    if rest and len(picked) > len(rest) * 2:
        times = min(3, len(picked) // len(rest))
        rest = rest * max(1, times)
    balanced = picked + rest
    rng.shuffle(balanced)
    return balanced


def _farthest(vectors: np.ndarray, k: int) -> np.ndarray:
    """Indexes of a diverse support set. One mean cannot cover every language."""
    count = vectors.shape[0]
    if count <= k:
        return np.arange(count)
    selected = [int(np.argmax(np.linalg.norm(vectors - vectors.mean(axis=0), axis=1)))]
    while len(selected) < k:
        dists = [np.linalg.norm(vectors - vectors[index], axis=1) for index in selected]
        selected.append(int(np.argmax(np.min(np.vstack(dists), axis=0))))
    return np.array(selected, dtype=np.int64)


def _prototypes(embeddings: np.ndarray, rows: list[tuple], k: int = 10) -> tuple[np.ndarray, np.ndarray]:
    families = ["gas", "co", "electrical", "flood", "water_electric", "sewage", "comfort"]
    chunks = []
    flags = []
    for family in families:
        idx = [i for i, row in enumerate(rows) if row[1] == "emergency" and row[3] == family]
        if not idx:
            continue
        block = embeddings[np.array(idx)]
        chosen = block[_farthest(block, k)]
        chunks.append(chosen)
        flags.extend([1] * chosen.shape[0])
    idx = [i for i, row in enumerate(rows) if row[1] in {"routine", "other"}]
    block = embeddings[np.array(idx)]
    chosen = block[_farthest(block, k * 2)]
    chunks.append(chosen)
    flags.extend([0] * chosen.shape[0])
    return np.vstack(chunks).astype(np.float32), np.array(flags, dtype=np.int8)


def main() -> None:
    rng = random.Random(SEED)
    banned = _frozen_texts()
    raw = build(rng)
    rows = []
    seen: set[str] = set()
    for row in raw:
        key = " ".join(row[0].split()).casefold()
        if key in banned or key in seen:
            continue
        seen.add(key)
        rows.append(row)
    print(f"rows {len(rows)} banned {len(banned)}", flush=True)

    by_label: dict[str, list] = {}
    for row in rows:
        by_label.setdefault(row[1], []).append(row)
    train: list = []
    val: list = []
    for label, items in by_label.items():
        rng.shuffle(items)
        cut = max(1, int(len(items) * 0.2))
        val.extend(items[:cut])
        train.extend(items[cut:])
    train = _balance(train, rng)
    print(f"train {len(train)} val {len(val)}", flush=True)

    from evals.round13_heldout_set import HELDOUT as ROUND13
    from evals.round14_heldout_set import HELDOUT

    held = [(" ".join(text.split()), label, "other", family, language) for label, family, language, text in HELDOUT]
    round13 = [(" ".join(text.split()), label, "other", family, language) for label, family, language, text in ROUND13]
    texts = [row[0] for row in train + val + held + round13]
    vectors = _embed_unique(texts)
    n_train = len(train)
    n_val = len(val)
    n_held = len(held)
    train_x = vectors[:n_train]
    val_x = vectors[n_train : n_train + n_val]
    held_x = vectors[n_train + n_val : n_train + n_val + n_held]
    round13_x = vectors[n_train + n_val + n_held :]

    numpy_rng = np.random.default_rng(SEED)
    hazard_index = {label: index for index, label in enumerate(HAZARD_LABELS)}
    y_h = np.array([hazard_index[row[1]] for row in train], dtype=np.int64)
    print("fitting hazard head on e5 embeddings", flush=True)
    hazard_w, hazard_b = _fit(
        train_x,
        y_h,
        len(HAZARD_LABELS),
        numpy_rng,
        sample_w=np.ones(len(train), dtype=np.float64),
        l2=1e-5,
        epochs=180,
    )

    service_index = {label: index for index, label in enumerate(SERVICE_LABELS)}
    y_s = np.array([service_index.get(row[2], service_index["other"]) for row in train], dtype=np.int64)
    print("fitting service head", flush=True)
    service_w, service_b = _fit(
        train_x,
        y_s,
        len(SERVICE_LABELS),
        numpy_rng,
        sample_w=np.ones(len(train), dtype=np.float64),
        l2=1e-5,
        epochs=120,
    )

    val_probs = _probs(val_x, hazard_w, hazard_b)
    val_labels = [row[1] for row in val]
    em_mask = np.array([label == "emergency" for label in val_labels])
    rt_mask = np.array([label == "routine" for label in val_labels])
    print(
        f"mean P(em) emergency {val_probs[em_mask, 0].mean():.3f} routine {val_probs[rt_mask, 0].mean():.3f}",
        flush=True,
    )
    page_min, ask_min, margin, routine_lock, val_metrics = _search(val_probs, val_labels)
    held_probs = _probs(held_x, hazard_w, hazard_b)
    held_labels = [row[1] if row[1] in HAZARD_LABELS else "routine" for row in held]
    held_metrics = _score(held_probs, held_labels)
    by_family = _group_recall(held, held_probs, 3)
    by_language = _group_recall(held, held_probs, 4)
    print("held-out", json.dumps(held_metrics), flush=True)
    print("by family", json.dumps(by_family), flush=True)
    print("by language", json.dumps(by_language), flush=True)
    round13_labels = [row[1] if row[1] in HAZARD_LABELS else "routine" for row in round13]
    round13_metrics = _score(_probs(round13_x, hazard_w, hazard_b), round13_labels)
    print("round13 head-only", json.dumps(round13_metrics), flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUT,
        hazard_W=hazard_w,
        hazard_b=hazard_b,
        service_W=service_w,
        service_b=service_b,
        page_min=np.float32(page_min),
        ask_min=np.float32(ask_min),
        page_margin=np.float32(margin),
        routine_lock=np.float32(routine_lock),
    )
    payload = {
        "seed": SEED,
        "embedder": "intfloat/multilingual-e5-large",
        "head": "logistic-e5",
        "train_n": len(train),
        "val_n": len(val),
        "held_out_n": len(held),
        "thresholds": {
            "page_min": page_min,
            "ask_min": ask_min,
            "page_margin": margin,
            "routine_lock": routine_lock,
        },
        "validation": val_metrics,
        "held_out_head_only": held_metrics,
        "held_out_by_family": by_family,
        "held_out_by_language": by_language,
        "note": (
            "Head-only scores use the learned head before hand rules. "
            "The threshold was chosen on the synthetic validation split, then frozen. "
            "The held-out file was written before training and was excluded from the fit."
        ),
    }
    METRICS.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {OUT} and {METRICS}", flush=True)


if __name__ == "__main__":
    main()
