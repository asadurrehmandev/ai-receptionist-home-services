"""Score the round-8 frozen lines. Does not call Claude or the local model.

Run from the repo root: python -m evals.round8
A miss is printed. The process exits 0 so a partial score can be published.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.agent.hazard import classify_emergency
from app.agent.nlu import safety_decision
from evals.round8_set import ROUND8, SAFETY8

_EXPECT = {"transfer": "definite", "ask": "ask", "advice": "advice", "routine": "none"}


def score_round8() -> dict:
    misses: list[tuple[str, str, str | None, str]] = []
    counts = {label: [0, 0] for label in ("transfer", "ask", "routine")}
    false_pages = 0
    for label, text in ROUND8:
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
    for label, text in SAFETY8:
        got = safety_decision(text)
        safety_hits[label][1] += 1
        if got == label:
            safety_hits[label][0] += 1
        else:
            safety_misses.append((label, got, text))
    transfer_hit, transfer_total = counts["transfer"]
    routine_total = counts["routine"][1]
    return {
        "total": len(ROUND8),
        "counts": counts,
        "misses": misses,
        "recall": f"{transfer_hit}/{transfer_total}",
        "false_pages": false_pages,
        "false_page_rate": f"{false_pages}/{routine_total}",
        "safety": safety_hits,
        "safety_misses": safety_misses,
    }


def main() -> int:
    report = score_round8()
    print(f"frozen lines: {report['total']}")
    for label in ("transfer", "ask", "routine"):
        hit, total = report["counts"][label]
        print(f"  {label}: {hit}/{total}")
    print(f"emergency recall: {report['recall']}")
    print(f"routine false pages: {report['false_page_rate']}")
    for label in ("clear", "page"):
        hit, total = report["safety"][label]
        print(f"  safety {label}: {hit}/{total}")
    print("live Claude: not called")
    print("local instruct model: not called")
    print(f"misses: {len(report['misses'])}")
    for label, got, why, text in report["misses"]:
        print(f"  [{label} -> {got} {why}] {text}")
    print(f"safety misses: {len(report['safety_misses'])}")
    for label, got, text in report["safety_misses"]:
        print(f"  [{label} -> {got}] {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
