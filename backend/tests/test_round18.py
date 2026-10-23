"""Round 18: a head at or above 0.80 stays until a real routine matches.

A fixture, a drip, or the word emergency is not that match. The held-out
file was hashed before this round's policy edit. Do not edit its lines to
lift a score. Do not move the page cut.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.agent.calendar import MemoryCalendar
from app.agent.engine import Engine, SessionState
from app.agent.hazard import classify_emergency
from app.agent.nlu import detect_language, extract_issue
from app.config_loader import load_business
from app.service import FixedClock
from evals.round18_heldout_set import HELDOUT

ROOT = Path(__file__).resolve().parents[2]
THU = datetime(2026, 10, 22, 9, 0, tzinfo=ZoneInfo("America/Chicago"))
CONFIG = load_business(ROOT / "config" / "business.yaml")
HELDOUT_SHA = "12a7ab82306727b43a91a27f50c2c6d7462427aee33cd0aac756af77ed0629ed"


def _engine() -> Engine:
    return Engine(CONFIG, MemoryCalendar(), FixedClock(THU))


def test_round18_heldout_file_is_unchanged():
    digest = hashlib.sha256((ROOT / "evals" / "round18_heldout_set.py").read_bytes()).hexdigest()
    assert digest == HELDOUT_SHA
    assert len(HELDOUT) >= 40


def test_page_cut_stays_put():
    from app.agent import hazard_head

    hazard_head._weights()
    assert round(hazard_head.PAGE_MIN, 2) == 0.55
    assert round(hazard_head.ASK_MIN, 2) == 0.55
    assert round(hazard_head.PAGE_MARGIN, 2) == 0.02
    assert round(hazard_head.ROUTINE_LOCK, 2) == 0.40


def test_yowling_unit_with_illness_and_a_drip_pages_as_carbon_monoxide():
    lines = [
        "The closet unit is yowling, my daughter feels faint, and the bath faucet drips.",
        "A box in the hall is wailing, I am nauseous, and there is a drip at the sink.",
    ]
    for line in lines:
        assert extract_issue(line) is None
        level, label = classify_emergency(line)
        assert level == "definite", (line, level, label)
        assert label == "Carbon monoxide"
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome == "escalated", line
        assert state.phase != "collect_name"
        assert "faucet" not in (state.issue or "").lower()
        lowered = heard.say.lower()
        assert "fresh air" in lowered or "outside" in lowered
        assert "smell gas" not in lowered
        assert "what's going on" not in lowered
        assert "name" not in lowered


def test_sewage_that_also_says_emergency_pages_and_does_not_ask_for_a_name():
    line = "This is an emergency. Dirty water is coming up through the hall toilet."
    assert extract_issue(line) is None
    level, label = classify_emergency(line)
    assert level == "definite", (level, label)
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.outcome == "escalated"
    assert state.phase != "collect_name"
    assert "toilet" not in (state.issue or "").lower()
    lowered = heard.say.lower()
    assert "sewage" in lowered
    assert "valve" not in lowered
    assert "name" not in lowered
    assert "what's going on" not in lowered


def test_a_denied_gas_and_smoke_list_stays_routine_in_spanish_and_portuguese():
    lines = [
        "No hay gas y no hay humo. Solo quiero cambiar el grifo.",
        "Não tem gás e não tem fumaça. Quero trocar a torneira.",
    ]
    for line in lines:
        level, label = classify_emergency(line)
        assert level != "definite", (line, level, label)
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome != "escalated", line
        lowered = heard.say.lower()
        assert "emergency dispatch" not in lowered
        assert "tarifa de emergencia" not in lowered


def test_a_past_failure_that_is_dry_now_stays_routine():
    lines = [
        "Last winter the hose let go. It is dry now. Please book a look.",
        "The washing-machine hose failed in March. Everything is dry today.",
    ]
    for line in lines:
        level, label = classify_emergency(line)
        assert level != "definite", (line, level, label)
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome != "escalated", line
        assert "emergency dispatch" not in heard.say.lower()


def test_a_plaster_circle_and_a_furnace_bang_ask():
    lines = [
        "A brown circle showed up on the plaster ceiling this morning.",
        "The furnace started banging after the heat came on.",
        "The boiler let out one bang and then went quiet.",
    ]
    for line in lines:
        level, _label = classify_emergency(line)
        assert level == "ask", (line, level, _label)
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome != "escalated"
        assert "danger" in heard.say.lower()


def test_a_water_heater_that_bangs_is_still_a_booking():
    level, _label = classify_emergency("The water heater is making a banging noise.")
    assert level == "none"


def test_portuguese_comfort_outside_the_old_hint_list_speaks_portuguese():
    line = "O neném ficou no berço, o quarto está frio e o aquecimento parou."
    assert detect_language(line) == "pt"
    level, label = classify_emergency(line)
    assert level == "definite", (level, label)
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.outcome == "escalated"
    assert state.language == "pt"
    lowered = heard.say.lower()
    assert "what's going on" not in lowered
    assert "aquecido" in lowered or "fresco" in lowered
    assert "smell gas" not in lowered


def test_a_high_head_is_not_cleared_by_a_fixture_or_the_word_emergency(monkeypatch):
    monkeypatch.setattr("app.agent.hazard_head.head_level", lambda text: ("definite", "Hazard"))
    monkeypatch.setattr("app.agent.hazard._emergency_probability", lambda text: 0.86)
    line = "The hall toilet is an emergency."
    level, _label = classify_emergency(line)
    assert level in {"definite", "ask"}
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.phase != "collect_name"
    assert "name" not in heard.say.lower()
    assert state.outcome == "escalated" or state.phase == "hazard_check"


def test_the_second_turn_that_names_neither_asks_safety_and_a_clean_no_calls_back():
    engine = _engine()
    state = SessionState()
    first = engine.handle(state, "It is difficult to describe from the driveway.")
    assert "what's going on" in first.say.lower()
    assert state.issue is None
    second = engine.handle(state, "blah blah blah")
    assert "danger" in second.say.lower()
    assert state.phase == "unclear_handoff"
    answer = engine.handle(state, "no")
    assert state.outcome != "escalated"
    assert state.phase == "callback_offer"
    assert "phone" not in answer.say.lower()
    assert "call you back" in answer.say.lower()
