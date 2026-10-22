"""The round-6 file was frozen before the class rules. The score is the post-tune result."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.unseen import score_unseen
from evals.unseen_set import UNSEEN


def test_unseen_file_stays_frozen():
    assert len(UNSEEN) == 58
    labels = {label for label, _text in UNSEEN}
    assert labels == {"transfer", "ask", "advice", "routine"}
    assert sum(1 for label, _text in UNSEEN if label == "transfer") == 36
    assert sum(1 for label, _text in UNSEEN if label == "routine") == 18


def test_unseen_post_tune_score():
    """Before the class rules this file scored 17/36 and 1/18 false pages."""
    report = score_unseen()
    hit, total = report["counts"]["transfer"]
    assert total == 36
    assert hit == 36
    assert report["false_pages"] == 0
    assert report["counts"]["routine"] == [18, 18]
