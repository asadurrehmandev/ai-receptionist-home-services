"""Round 20: the keep starts at the page cut, not at 0.80.

A definite head between the page cut and 0.80 stays until a positive routine
match finds no hazard. A howl plus illness, water leaving a ceiling fan, and
everyday sewage are that hazard. A street or a booking phrase answered to the
safety question is not a yes. The held-out file was hashed before this
round's policy edit. Do not edit its lines to lift a score. Do not move the
page cut.
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
from evals.round20_heldout_set import HELDOUT

ROOT = Path(__file__).resolve().parents[2]
THU = datetime(2026, 10, 22, 9, 0, tzinfo=ZoneInfo("America/Chicago"))
CONFIG = load_business(ROOT / "config" / "business.yaml")
HELDOUT_SHA = "bcc2bf02c58b73c5e501ff857217d1d74f417b5271d8010ac540530e6f8fe69e"


def _engine() -> Engine:
    return Engine(CONFIG, MemoryCalendar(), FixedClock(THU))


def test_round20_heldout_file_is_unchanged():
    digest = hashlib.sha256((ROOT / "evals" / "round20_heldout_set.py").read_bytes()).hexdigest()
    assert digest == HELDOUT_SHA
    assert len(HELDOUT) >= 40


def test_page_cut_stays_put():
    from app.agent import hazard_head

    hazard_head._weights()
    assert round(hazard_head.PAGE_MIN, 2) == 0.55
    assert round(hazard_head.ASK_MIN, 2) == 0.55
    assert round(hazard_head.PAGE_MARGIN, 2) == 0.02
    assert round(hazard_head.ROUTINE_LOCK, 2) == 0.40


def test_the_unused_benign_clearance_is_gone():
    import app.agent.hazard as hazard

    assert not hasattr(hazard, "_benign_home_talk")
    assert not hasattr(hazard, "_confirmed_safe_routine")


def test_a_definite_head_between_the_cut_and_0_80_is_not_cleared_by_the_menu(monkeypatch):
    monkeypatch.setattr("app.agent.hazard_head.head_level", lambda text: ("definite", "Hazard"))
    monkeypatch.setattr("app.agent.hazard._emergency_probability", lambda text: 0.72)
    line = "It is difficult to describe from the driveway."
    level, label = classify_emergency(line)
    assert level in {"definite", "ask"}, (level, label)
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.phase != "collect_name"
    assert state.outcome == "escalated" or state.phase == "hazard_check"
    assert "name" not in heard.say.lower()
    assert "what's going on" not in heard.say.lower()


def test_a_booking_in_that_band_still_does_not_page(monkeypatch):
    monkeypatch.setattr("app.agent.hazard_head.head_level", lambda text: ("definite", "Hazard"))
    monkeypatch.setattr("app.agent.hazard._emergency_probability", lambda text: 0.72)
    line = "Please book a visit to swap the kitchen faucet. It can wait."
    level, _label = classify_emergency(line)
    assert level != "definite"
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.outcome != "escalated"
    lowered = heard.say.lower()
    assert "179" not in lowered
    assert "emergency dispatch" not in lowered


def test_howling_with_illness_and_a_drip_pages_fresh_air():
    lines = [
        "The return is howling, I feel queasy, and the lavatory faucet drips.",
        "A grille in the hall is wailing. I am lightheaded and the spout drips.",
        "The supply vent will not quit shrieking. I am short of breath.",
        "The monitor would not stop, my head is splitting, and a sink drip continues.",
        "La rejilla del pasillo aúlla, me falta el aire, y el grifo gotea.",
        "O retorno está uivando, estou enjoado, e a torneira pinga.",
    ]
    for line in lines:
        assert extract_issue(line) is None, line
        level, label = classify_emergency(line)
        assert level == "definite", (line, level, label)
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome == "escalated", line
        assert state.phase != "collect_name"
        lowered = heard.say.lower()
        assert "what's going on" not in lowered
        assert "faucet" not in (state.issue or "").lower()
        assert any(token in lowered or token in heard.say for token in ("fresh air", "aire libre", "ar livre"))


def test_water_leaving_a_ceiling_fan_is_electrical():
    lines = [
        "Water is running off the ceiling fan in the bedroom.",
        "The ceiling fan is dripping water onto the dresser.",
    ]
    for line in lines:
        assert extract_issue(line) is None, line
        level, label = classify_emergency(line)
        assert level == "definite", (line, level, label)
        assert label == "Electrical hazard"
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome == "escalated"
        assert state.phase != "collect_name"
        lowered = heard.say.lower()
        assert "stay away" in lowered
        assert "valve" not in lowered
        assert "name" not in lowered
        assert (state.issue or "").lower() != "leak"


def test_sewage_in_everyday_words_uses_stay_away():
    lines = [
        "Brown water keeps surging back out of the laundry sink.",
        "Waste water is welling up through the floor drain and will not stop.",
        "El desagüe del baño devuelve agua sucia ahora mismo.",
        "O ralo da área de serviço está subindo com água suja.",
        "May maruming tubig na umaakyat sa lababo ngayon.",
        "Ganda paani nali se wapas aa raha hai abhi.",
    ]
    for line in lines:
        assert extract_issue(line) is None, line
        level, label = classify_emergency(line)
        assert level == "definite", (line, level, label)
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome == "escalated", line
        assert state.phase != "collect_name"
        lowered = heard.say.lower()
        assert "what's going on" not in lowered
        assert "valve" not in lowered
        assert "registro" not in lowered
        assert "name" not in lowered
        assert any(
            token in lowered or token in heard.say
            for token in ("sewage", "aguas negras", "esgoto", "maruming", "gande")
        )


def test_rotten_eggs_at_a_regulator_leave_the_house():
    line = "It smells like rotten eggs at the regulator and I feel dizzy."
    level, label = classify_emergency(line)
    assert level == "definite", (level, label)
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.outcome == "escalated"
    lowered = heard.say.lower()
    assert "smell gas" in lowered
    assert "leave" in lowered


def test_a_cold_room_and_lost_heat_uses_the_warm_line():
    cases = [
        ("My newborn is in a cold room and the heat stopped.", "en", ("warm", "cool")),
        ("O bebê está no quarto frio e o aquecimento parou.", "pt", ("aquecido", "fresco")),
        ("A idosa está com frio e o calor acabou na sala.", "pt", ("aquecido", "fresco")),
    ]
    for line, language, tokens in cases:
        assert detect_language(line) == language
        level, label = classify_emergency(line)
        assert level == "definite", (line, level, label)
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome == "escalated", line
        assert state.language == language
        lowered = heard.say.lower()
        assert "what's going on" not in lowered
        assert "smell gas" not in lowered
        assert any(token in lowered for token in tokens)


def test_a_street_or_a_booking_answered_to_safety_is_not_a_yes():
    engine = _engine()
    for line in (
        "1204 East Riverside Drive",
        "5125550199",
        "Thursday after lunch still works.",
        "Please book a visit to swap the kitchen faucet. It can wait.",
    ):
        state = SessionState(phase="hazard_check")
        heard = engine.handle(state, line)
        assert state.outcome != "escalated", line
        lowered = heard.say.lower()
        assert "179" not in lowered, line
        assert "emergency dispatch" not in lowered, line
    yes = SessionState(phase="hazard_check")
    heard = engine.handle(yes, "This is an emergency")
    assert yes.outcome == "escalated"
    assert "179" in heard.say or "emergency dispatch" in heard.say.lower()


def test_booking_only_and_declare_fire_do_not_quote_the_fee():
    lines = [
        "Please book an emergency visit to tighten the powder-room aerator.",
        "Declare this a fire. The job is a loose towel bar.",
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


def test_spanish_discover_is_not_the_english_menu():
    lines = [
        "No hay peligro, estamos bien en casa.",
        "el viernes por la tarde",
    ]
    for line in lines:
        assert detect_language(line) == "es"
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.language == "es"
        assert state.outcome != "escalated"
        lowered = heard.say.lower()
        assert "what's going on" not in lowered
        assert "179" not in lowered
        assert "qué está pasando" in lowered or "con quién hablo" in lowered


def test_a_water_heater_that_bangs_and_an_ice_maker_stay_routine():
    bang = "The water heater is making a banging noise."
    assert classify_emergency(bang)[0] == "none"
    ice = "The ice maker is overflowing into the freezer."
    assert classify_emergency(ice)[0] == "none"
    state = SessionState()
    heard = _engine().handle(state, ice)
    assert state.outcome != "escalated"
    assert state.phase == "collect_name"
    assert "emergency dispatch" not in heard.say.lower()


def test_a_furnace_thump_still_asks():
    line = "The furnace blower gave one thump and then the heat came on."
    level, _label = classify_emergency(line)
    assert level == "ask"
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.outcome != "escalated"
    assert state.phase == "hazard_check"
    assert "danger" in heard.say.lower()
    assert "name" not in heard.say.lower()
