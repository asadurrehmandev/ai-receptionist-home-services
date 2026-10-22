"""The held-out hazard file stays frozen. The score is published, not forced to 100%."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.heldout import score_heldout
from evals.heldout_set import HELDOUT


def test_heldout_set_was_written_before_tuning():
    assert len(HELDOUT) == 97
    labels = {label for label, _text in HELDOUT}
    assert labels == {"transfer", "ask", "advice", "routine"}


def test_heldout_recall_does_not_fall_below_the_pre_tune_floor():
    report = score_heldout()
    hit, total = report["counts"]["transfer"]
    assert total == 48
    assert hit >= 28
    assert report["false_pages"] <= 3
