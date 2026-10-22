"""Score the round-11 desk lines. Does not call Claude.

Run from the repo root: python -m evals.round11
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
from evals.round11_set import ROUND11

_EXPECT = {"transfer": "definite", "ask": "ask", "routine": "none"}


def line_hash() -> str:
    payload = "\n".join(f"{label}\t{text}" for label, text in ROUND11)
    return hashlib.sha256(payload.encode()).hexdigest()


def score_round11() -> dict:
    misses: list[tuple[str, str, str | None, str]] = []
    counts = {label: [0, 0] for label in ("transfer", "ask", "routine")}
    false_pages = 0
    for label, text in ROUND11:
        got, why = classify_emergency(text)
        counts[label][1] += 1
        if got == _EXPECT[label]:
            counts[label][0] += 1
        else:
            misses.append((label, got, why, text))
            if label == "routine" and got == "definite":
                false_pages += 1
    return {
        "total": len(ROUND11),
        "counts": counts,
        "misses": misses,
        "false_pages": false_pages,
        "line_hash": line_hash(),
    }


def main() -> int:
    report = score_round11()
    print(f"line sha256: {report['line_hash']}")
    print(f"desk lines: {report['total']}")
    for label in ("transfer", "ask", "routine"):
        hit, total = report["counts"][label]
        print(f"  {label}: {hit}/{total}")
    print(f"routine false pages: {report['false_pages']}/{report['counts']['routine'][1]}")
    print(f"misses: {len(report['misses'])}")
    for label, got, why, text in report["misses"]:
        print(f"  [{label} -> {got} {why}] {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
