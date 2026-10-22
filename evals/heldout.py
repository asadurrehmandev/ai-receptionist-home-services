"""Score the held-out hazard lines. Does not call Claude.

Run from the repo root: python -m evals.heldout
A miss is printed. The process still exits 0 so a partial score can be published.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.agent.hazard import classify_emergency
from evals.heldout_set import HELDOUT

_EXPECT = {"transfer": "definite", "ask": "ask", "advice": "advice", "routine": "none"}


def score_heldout() -> dict:
    misses: list[tuple[str, str, str | None, str]] = []
    counts = {label: [0, 0] for label in _EXPECT}
    false_pages = 0
    for label, text in HELDOUT:
        got, why = classify_emergency(text)
        counts[label][1] += 1
        if got == _EXPECT[label]:
            counts[label][0] += 1
        else:
            misses.append((label, got, why, text))
            if label == "routine" and got == "definite":
                false_pages += 1
    transfer_hit, transfer_total = counts["transfer"]
    return {
        "total": len(HELDOUT),
        "counts": counts,
        "misses": misses,
        "recall": f"{transfer_hit}/{transfer_total}",
        "false_pages": false_pages,
    }


def main() -> int:
    report = score_heldout()
    print(f"held-out lines: {report['total']}")
    for label in ("transfer", "ask", "advice", "routine"):
        hit, total = report["counts"][label]
        print(f"  {label}: {hit}/{total}")
    print(f"emergency recall: {report['recall']}")
    print(f"routine false pages: {report['false_pages']}")
    print("live Claude: not called")
    print(f"misses: {len(report['misses'])}")
    for label, got, why, text in report["misses"]:
        print(f"  [{label} -> {got} {why}] {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
