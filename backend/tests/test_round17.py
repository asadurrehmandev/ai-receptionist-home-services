"""Round 17: a head at or above 0.80 is kept before a routine clearance.

The held-out file was hashed before this round's policy edit. Do not edit
its lines to lift a score. Do not move the page cut.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.agent.calendar import MemoryCalendar
from app.agent.engine import Engine, SessionState
from app.agent.hazard import classify_emergency
from app.agent.nlu import detect_language
from app.config_loader import load_business
from app.service import FixedClock
from evals.round17_heldout_set import HELDOUT

ROOT = Path(__file__).resolve().parents[2]
THU = datetime(2026, 10, 22, 9, 0, tzinfo=ZoneInfo("America/Chicago"))
CONFIG = load_business(ROOT / "config" / "business.yaml")
HELDOUT_SHA = "38bb371951c67e73b4e9d2d4752fade8a70f5a249655b1da0d417eb3c9cae5fe"


def _engine() -> Engine:
    return Engine(CONFIG, MemoryCalendar(), FixedClock(THU))


def test_round17_heldout_file_is_unchanged():
    digest = hashlib.sha256((ROOT / "evals" / "round17_heldout_set.py").read_bytes()).hexdigest()
    assert digest == HELDOUT_SHA
    assert len(HELDOUT) >= 40


def test_page_cut_stays_put():
    from app.agent import hazard_head

    hazard_head._weights()
    assert round(hazard_head.PAGE_MIN, 2) == 0.55
    assert round(hazard_head.ASK_MIN, 2) == 0.55
    assert round(hazard_head.PAGE_MARGIN, 2) == 0.02
    assert round(hazard_head.ROUTINE_LOCK, 2) == 0.40


def test_a_high_head_survives_spanish_intent_when_present_hazard_misses(monkeypatch):
    monkeypatch.setattr("app.agent.hazard_head.head_level", lambda text: ("definite", "Hazard"))
    monkeypatch.setattr("app.agent.hazard._emergency_probability", lambda text: 0.91)
    monkeypatch.setattr("app.agent.hazard._sewage_active", lambda text: False)
    monkeypatch.setattr("app.agent.hazard._present_hazard_clause", lambda text: False)
    monkeypatch.setattr("app.agent.hazard._sounding_detector", lambda text: False)
    monkeypatch.setattr("app.agent.hazard._uncontrolled_water", lambda text: False)
    monkeypatch.setattr("app.agent.hazard._uncontrolled_water_now", lambda text: False)
    line = "El desagüe del baño está devolviendo agua sucia y no para."
    level, _label = classify_emergency(line)
    assert level in {"definite", "ask"}
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.phase != "collect_name"
    assert state.outcome == "escalated" or state.phase == "hazard_check"
    assert "nombre" not in heard.say.lower()
    lowered = heard.say.lower()
    assert "what's going on" not in lowered
    assert "what seems to be the problem" not in lowered


def test_a_spanish_heater_that_can_wait_still_books_at_a_high_head(monkeypatch):
    monkeypatch.setattr("app.agent.hazard_head.head_level", lambda text: ("definite", "Hazard"))
    monkeypatch.setattr("app.agent.hazard._emergency_probability", lambda text: 0.91)
    line = "Necesito reparar el calentador y puede esperar."
    assert classify_emergency(line)[0] != "definite"
    state = SessionState()
    _engine().handle(state, line)
    assert state.outcome != "escalated"


def test_spanish_sewage_without_the_textbook_noun_pages():
    lines = [
        "El desagüe del baño está devolviendo agua sucia y no para.",
        "Sale agua podrida por la coladera y hay un goteo en el lavabo.",
    ]
    for line in lines:
        level, _label = classify_emergency(line)
        assert level == "definite", (line, level, _label)
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome == "escalated", line
        assert state.language == "es"
        lowered = heard.say.lower()
        assert "what's going on" not in lowered
        assert "nombre" not in lowered
        assert "aguas" in lowered or "negras" in lowered or "alcantar" in lowered or "sewage" in lowered
        assert "huele a gas" not in lowered


def test_a_howling_unit_with_illness_pages_even_with_a_drip():
    lines = [
        "The white unit in the hall is howling and my son feels sick.",
        "Something on the ceiling is screaming, I am dizzy, and the sink drips.",
        "El aparato del pasillo está aullando y me duele la cabeza.",
    ]
    for line in lines:
        level, label = classify_emergency(line)
        assert level == "definite", (line, level, label)
        assert label == "Carbon monoxide", (line, label)
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome == "escalated", line
        lowered = heard.say.lower()
        assert "smell gas" not in lowered
        assert "huele a gas" not in lowered
        assert any(token in lowered for token in ("fresh air", "outside", "aire libre", "afuera"))


def test_portuguese_comfort_is_detected_and_uses_the_warm_script():
    line = "O bebê está aqui, a casa está gelada e o aquecedor não liga."
    assert detect_language(line) == "pt"
    level, label = classify_emergency(line)
    assert level == "definite", (level, label)
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.language == "pt"
    assert state.outcome == "escalated"
    lowered = heard.say.lower()
    assert "what's going on" not in lowered
    assert "smell gas" not in lowered
    assert "aquecido" in lowered or "fresco" in lowered


def test_a_ceiling_mark_and_a_knocking_boiler_ask_instead_of_clearing(monkeypatch):
    monkeypatch.setattr("app.agent.hazard_head.head_level", lambda text: ("definite", "Hazard"))
    monkeypatch.setattr("app.agent.hazard._emergency_probability", lambda text: 0.86)
    for line in (
        "A dark mark showed up on the bedroom ceiling this afternoon.",
        "The boiler started knocking after we turned the heat on.",
    ):
        level, _label = classify_emergency(line)
        assert level == "ask", (line, level, _label)
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome != "escalated"
        assert "danger" in heard.say.lower()


def test_a_booking_that_only_says_emergency_does_not_quote_the_fee():
    line = "Please book an emergency visit to tighten the hall-bath aerator."
    assert classify_emergency(line)[0] != "definite"
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.outcome != "escalated"
    assert "emergency dispatch" not in heard.say.lower()
    assert "tarifa de emergencia" not in heard.say.lower()
