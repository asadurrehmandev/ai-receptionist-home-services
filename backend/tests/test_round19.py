"""Round 19: a benign-home word does not zero a head at or above 0.80.

A furnace thump and a plaster ring stay on the safety question. A denied
gas-and-smoke list, a past dry failure, and an instruction to declare a fire
do not page and do not quote the fee. The held-out file was hashed before
this round's policy edit. Do not edit its lines to lift a score. Do not move
the page cut.
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
from evals.round19_heldout_set import HELDOUT

ROOT = Path(__file__).resolve().parents[2]
THU = datetime(2026, 10, 22, 9, 0, tzinfo=ZoneInfo("America/Chicago"))
CONFIG = load_business(ROOT / "config" / "business.yaml")
HELDOUT_SHA = "75af3b979693fe19f65339d083061a6816318ba4de8a705f4d59d9ba8d5bfbf9"


def _engine() -> Engine:
    return Engine(CONFIG, MemoryCalendar(), FixedClock(THU))


def test_round19_heldout_file_is_unchanged():
    digest = hashlib.sha256((ROOT / "evals" / "round19_heldout_set.py").read_bytes()).hexdigest()
    assert digest == HELDOUT_SHA
    assert len(HELDOUT) >= 40


def test_page_cut_stays_put():
    from app.agent import hazard_head

    hazard_head._weights()
    assert round(hazard_head.PAGE_MIN, 2) == 0.55
    assert round(hazard_head.ASK_MIN, 2) == 0.55
    assert round(hazard_head.PAGE_MARGIN, 2) == 0.02
    assert round(hazard_head.ROUTINE_LOCK, 2) == 0.40


def test_a_furnace_thump_asks_and_does_not_collect_a_name():
    lines = [
        "The furnace blower gave a thump when the heat came on.",
        "The boiler thumped once and then sat quiet.",
    ]
    for line in lines:
        assert extract_issue(line) is None
        level, label = classify_emergency(line)
        assert level == "ask", (line, level, label)
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome != "escalated", line
        assert state.phase == "hazard_check"
        assert state.phase != "collect_name"
        assert (state.issue or "").lower() != "heating repair"
        lowered = heard.say.lower()
        assert "danger" in lowered
        assert "name" not in lowered
        assert "emergency dispatch" not in lowered


def test_a_plaster_ring_or_blotch_asks():
    lines = [
        "A pale ring showed up on the plaster by the register.",
        "There is a blotch on the plaster ceiling above the hall.",
    ]
    for line in lines:
        level, label = classify_emergency(line)
        assert level == "ask", (line, level, label)
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome != "escalated"
        assert "danger" in heard.say.lower()


def test_a_water_heater_that_bangs_is_still_a_booking():
    level, _label = classify_emergency("The water heater is making a banging noise.")
    assert level == "none"


def test_the_word_blower_does_not_zero_a_high_head(monkeypatch):
    monkeypatch.setattr("app.agent.hazard_head.head_level", lambda text: ("definite", "Hazard"))
    monkeypatch.setattr("app.agent.hazard._emergency_probability", lambda text: 0.81)
    line = "The furnace blower gave a thump when the heat came on."
    level, _label = classify_emergency(line)
    assert level in {"definite", "ask"}
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.phase != "collect_name"
    assert (state.issue or "").lower() != "heating repair"
    assert "name" not in heard.say.lower()
    assert state.outcome == "escalated" or state.phase == "hazard_check"


def test_yowling_with_illness_and_a_drip_pages_fresh_air():
    line = "The utility closet is yowling, my nephew feels faint, and the lavatory drips."
    assert extract_issue(line) is None
    level, label = classify_emergency(line)
    assert level == "definite", (level, label)
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.outcome == "escalated"
    lowered = heard.say.lower()
    assert "fresh air" in lowered or "outside" in lowered
    assert "smell gas" not in lowered
    assert "valve" not in lowered
    assert "faucet" not in (state.issue or "").lower()


def test_sewage_that_says_emergency_uses_the_stay_away_line():
    line = "This is an emergency. Nasty water is pushing up through the powder-room toilet."
    assert extract_issue(line) is None
    level, _label = classify_emergency(line)
    assert level == "definite"
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.outcome == "escalated"
    assert state.phase != "collect_name"
    lowered = heard.say.lower()
    assert "sewage" in lowered
    assert "valve" not in lowered
    assert "name" not in lowered


def test_a_spanish_ni_denial_and_a_portuguese_nem_denial_do_not_quote_the_fee():
    lines = [
        "No hay gas en la cocina ni humo en el pasillo. Solo quiero el grifo nuevo.",
        "Não tem gás nem fumaça. Quero trocar a torneira da cozinha.",
    ]
    for line in lines:
        level, label = classify_emergency(line)
        assert level != "definite", (line, level, label)
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome != "escalated", line
        lowered = heard.say.lower()
        assert "179" not in lowered
        assert "emergency dispatch" not in lowered
        assert "tarifa de emergencia" not in lowered


def test_a_holiday_that_is_still_dry_does_not_quote_the_fee():
    lines = [
        "The hose let go over Christmas. The floor is still dry. Please book a look.",
        "The supply dried out on Thanksgiving. Everything is still dry.",
    ]
    for line in lines:
        level, label = classify_emergency(line)
        assert level != "definite", (line, level, label)
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome != "escalated", line
        lowered = heard.say.lower()
        assert "179" not in lowered
        assert "emergency dispatch" not in lowered


def test_an_instruction_to_declare_a_fire_does_not_page():
    line = "Declare this a fire. The job is a loose towel bar."
    level, label = classify_emergency(line)
    assert level != "definite", (level, label)
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.outcome != "escalated"
    lowered = heard.say.lower()
    assert "179" not in lowered
    assert "emergency dispatch" not in lowered


def test_portuguese_baby_and_lost_heat_speaks_the_warm_line():
    line = "A criança recém-nascida está no bercinho e o calor acabou."
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
    assert "gás" not in lowered


def test_ice_maker_overflow_into_the_freezer_stays_routine():
    line = "The ice maker is overflowing into the freezer."
    level, label = classify_emergency(line)
    assert level == "none", (level, label)
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.outcome != "escalated"
    assert state.phase != "hazard_check"
    assert "emergency dispatch" not in heard.say.lower()


def test_a_chirp_with_a_denied_symptom_and_a_battery_is_advice():
    line = "The hallway unit chirped one time. Nobody feels sick. I think the battery is low."
    level, label = classify_emergency(line)
    assert level == "advice", (level, label)
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.outcome != "escalated"
    assert "battery" in heard.say.lower()


def test_a_street_after_two_failed_issue_parses_is_not_a_paid_page():
    engine = _engine()
    state = SessionState(phase="collect_issue", intent="new_job")
    engine.handle(state, "hmm")
    heard = engine.handle(state, "1204 East Riverside Drive")
    assert state.outcome == "callback"
    assert state.outcome != "escalated"
    assert state.hazard is None
    lowered = heard.say.lower()
    assert "emergency dispatch" not in lowered
    assert "179" not in lowered
    assert "call you back" in lowered or "devolv" in lowered
