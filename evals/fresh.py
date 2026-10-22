"""Score the frozen caller lines with the hazard detector.

This is the rules-engine concept check. It does not call Claude.
Run from the repo root: python -m evals.fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.agent.hazard import classify_emergency
from evals.fresh_set import FRESH

_EXPECT = {"transfer": "definite", "advice": "advice", "routine": "none"}


def score_fresh() -> dict:
    misses: list[tuple[str, str, str | None, str]] = []
    counts = {label: [0, 0] for label in _EXPECT}
    for label, text in FRESH:
        got, why = classify_emergency(text)
        counts[label][1] += 1
        if got == _EXPECT[label]:
            counts[label][0] += 1
        else:
            misses.append((label, got, why, text))
    return {"total": len(FRESH), "counts": counts, "misses": misses}


def main() -> int:
    report = score_fresh()
    counts = report["counts"]
    print(f"frozen lines: {report['total']}")
    for label in ("transfer", "advice", "routine"):
        hit, total = counts[label]
        print(f"  {label}: {hit}/{total}")
    transfer_hit, transfer_total = counts["transfer"]
    routine_hit, routine_total = counts["routine"]
    false_alarms = routine_total - routine_hit
    print(f"emergency recall: {transfer_hit}/{transfer_total}")
    print(f"routine false escalations: {false_alarms}/{routine_total}")
    print("live Claude: not called")
    if report["misses"]:
        print(f"misses: {len(report['misses'])}")
        for label, got, why, text in report["misses"]:
            print(f"  [{label} -> {got} {why}] {text}")
        return 1
    print("misses: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
