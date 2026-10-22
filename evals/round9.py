"""Score the round-9 dev lines. Does not call Claude or a local model.

Run from the repo root: python -m evals.round9
A miss is printed. The process exits 0 so a partial score can be published.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.agent.hazard import classify_emergency
from app.agent.nlu import safety_decision
from evals.round9_set import ROUND9, SAFETY9

_EXPECT = {"transfer": "definite", "ask": "ask", "advice": "advice", "routine": "none"}


def line_hash() -> str:
    payload = "\n".join(f"{label}\t{text}" for label, text in (*ROUND9, *SAFETY9))
    return hashlib.sha256(payload.encode()).hexdigest()


def score_round9() -> dict:
    misses: list[tuple[str, str, str | None, str]] = []
    counts = {label: [0, 0] for label in ("transfer", "routine")}
    false_pages = 0
    for label, text in ROUND9:
        got, why = classify_emergency(text)
        counts[label][1] += 1
        if got == _EXPECT[label]:
            counts[label][0] += 1
        else:
            misses.append((label, got, why, text))
            if label == "routine" and got == "definite":
                false_pages += 1
    safety_hits = {"clear": [0, 0], "page": [0, 0]}
    safety_misses: list[tuple[str, str, str]] = []
    for label, text in SAFETY9:
        got = safety_decision(text)
        safety_hits[label][1] += 1
        if got == label:
            safety_hits[label][0] += 1
        else:
            safety_misses.append((label, got, text))
    return {
        "total": len(ROUND9),
        "counts": counts,
        "misses": misses,
        "false_pages": false_pages,
        "safety": safety_hits,
        "safety_misses": safety_misses,
        "line_hash": line_hash(),
    }


def main() -> int:
    report = score_round9()
    print(f"line sha256: {report['line_hash']}")
    print(f"frozen lines: {report['total']}")
    for label in ("transfer", "routine"):
        hit, total = report["counts"][label]
        print(f"  {label}: {hit}/{total}")
    print(f"routine false pages: {report['false_pages']}/{report['counts']['routine'][1]}")
    for label in ("clear", "page"):
        hit, total = report["safety"][label]
        print(f"  safety {label}: {hit}/{total}")
    print("live Claude: not called")
    print("local instruct model: not on this path")
    print(f"misses: {len(report['misses'])}")
    for label, got, why, text in report["misses"]:
        print(f"  [{label} -> {got} {why}] {text}")
    print(f"safety misses: {len(report['safety_misses'])}")
    for label, got, text in report["safety_misses"]:
        print(f"  [{label} -> {got}] {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
