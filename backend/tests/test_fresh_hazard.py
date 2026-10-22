"""Regression gate for the frozen lines in evals/fresh_set.py.

Those sentences were written for this desk. They are not a review file.
A miss fails here so the README number cannot drift silently.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.fresh import score_fresh
from evals.fresh_set import FRESH


def test_frozen_set_is_large_and_labeled():
    assert len(FRESH) >= 100
    labels = {label for label, _text in FRESH}
    assert labels == {"transfer", "advice", "routine"}


def test_hazard_concepts_match_the_frozen_labels():
    report = score_fresh()
    assert report["misses"] == []
    assert report["counts"]["transfer"] == [57, 57]
    assert report["counts"]["advice"] == [5, 5]
    assert report["counts"]["routine"] == [81, 81]
