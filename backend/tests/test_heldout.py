"""Held-out callers for the rules engine and the tool-calling dialog."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app.agent.calendar import MemoryCalendar
from app.agent.dialog import Dialog
from app.agent.engine import Engine
from app.config_loader import load_business
from app.llm.scripted import ScriptedToolModel
from app.service import FixedClock
from tests.heldout_callers import CASES, THU, dana, score_case

CONFIG = load_business(Path(__file__).resolve().parents[2] / "config" / "business.yaml")


def _run(case, model=None):
    now = datetime.fromisoformat(case["now"]) if case.get("now") else THU
    calendar = MemoryCalendar()
    if case.get("preload"):
        dana(calendar)
    engine = Engine(CONFIG, calendar, FixedClock(now))
    dialog = Dialog(engine, model) if model is not None else None
    return score_case(engine, case, calendar, dialog)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_rules_heldout(case):
    result = _run(case)
    assert result["ok"], (result["fails"], result["transcript"][-1])


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_tool_mode_heldout(case):
    result = _run(case, ScriptedToolModel())
    assert result["ok"], (result["fails"], result["transcript"][-1])
