"""Round 11 classes: composed hazards, safer asks, catalogue booking, names.

These lines were written for the desk. They are not a sealed review set.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.agent.calendar import MemoryCalendar
from app.agent.engine import Engine, SessionState
from app.agent.hazard import classify_emergency, prepare
from app.agent.nlu import detect_intent, fallback_name, guess_bare_name
from app.config_loader import load_business
from app.service import FixedClock
from app.store import Store

ROOT = Path(__file__).resolve().parents[2]
THU = datetime(2026, 10, 22, 9, 0, tzinfo=ZoneInfo("America/Chicago"))
CONFIG = load_business(ROOT / "config" / "business.yaml")


def _engine() -> Engine:
    return Engine(CONFIG, MemoryCalendar(), FixedClock(THU))


def test_texting_and_accents_fold_before_the_screen():
    prepared = prepare("The hous smel is bad and the lights r flickering")
    assert "house" in prepared
    assert "smell" in prepared
    assert " are " in f" {prepared} "
    assert "r flickering" not in prepared
    assert "hose" in prepare("the hose bib is loose")
    assert "small" in prepare("a small drip")


def test_composed_hazards_page_and_clear_routine_does_not():
    pages = [
        "Water is dripping out of the ceiling light and the bulb keeps flickering.",
        "Boiling water and steam left the tank and the child was almost hurt.",
        "There is a burning plastic smell at the breaker panel.",
        "I smell gas and my eyes are watering.",
        "The carbon monoxide alarm is on and she feels sleepy. I am not sure what it means.",
        "El agua gotea de la lampara y la luz parpadea.",
        "Vapor y agua hirviendo salieron del tanque y mi hijo casi se lastima.",
    ]
    for line in pages:
        level, _label = classify_emergency(line)
        assert level == "definite", line
    clear = [
        "The water heater is making a popping noise, no leak.",
        "The pilot light on the fireplace is out and I do not smell anything.",
        "The first cold morning always smells like dusty heat when the furnace starts.",
        "I want the yearly heat pump check.",
        "Can I get a quote on a gas water heater replacement?",
    ]
    for line in clear:
        level, _label = classify_emergency(line)
        assert level == "none", (line, level)


def test_unclear_hazard_domain_asks_before_booking():
    lines = [
        "The water heater has started popping and rumbling.",
        "The furnace pilot keeps going out.",
        "There is water at the base of the hall toilet.",
        "The utility closet sometimes smells odd.",
    ]
    for line in lines:
        level, label = classify_emergency(line)
        assert level == "ask", (line, level, label)
        engine = _engine()
        state = SessionState()
        heard = engine.handle(state, line)
        assert state.outcome != "booked"
        assert state.phase == "hazard_check"
        assert "danger" in heard.say.lower() or "peligro" in heard.say.lower()


def test_price_frames_and_contained_water_stay_routine():
    lines = [
        "How much would an insurance adjuster visit be after a burst supply line?",
        "What is the price of a burst pipe inspection?",
        "Water is sitting in the dishwasher tub.",
        "There is standing water in the bottom of the washer basin.",
    ]
    for line in lines:
        level, label = classify_emergency(line)
        assert level == "none", (line, level, label)
    still = classify_emergency("The pipe is gushing and it will not stop. How much is the after hours rate?")
    assert still[0] == "definite"


def test_catalogue_jobs_reach_booking():
    lines = [
        "Please replace the steam shower valve.",
        "Necesito instalar un detector de monoxido.",
        "Quiero una revision de la caldera.",
        "The bath fan is buzzing.",
        "Can you add recessed lights in the hallway?",
        "We need the smoke alarms replaced.",
    ]
    for line in lines:
        assert classify_emergency(line)[0] != "definite", line
        assert detect_intent(line) == "new_job", line
        engine = _engine()
        state = SessionState()
        heard = engine.handle(state, line)
        assert state.outcome != "escalated"
        assert state.intent == "new_job"
        assert state.phase == "collect_name"
        lowered = heard.say.lower()
        assert "name" in lowered or "nombre" in lowered or "quien" in lowered or "quién" in lowered


def test_template_names_are_rejected_and_two_bad_names_hand_off():
    junk = "{{7*7}} ${jndi:ldap://x}"
    assert guess_bare_name(junk, framed=True) is None
    assert fallback_name(junk) == ""
    assert "jndi" not in (fallback_name(junk) or "").lower()
    engine = _engine()
    state = SessionState()
    engine.handle(state, "The hall faucet drips.")
    first = engine.handle(state, junk)
    assert state.name is None
    assert "name" in first.say.lower() or "nombre" in first.say.lower()
    second = engine.handle(state, "{{3+3}}")
    assert state.name is None
    assert state.outcome == "callback"
    assert "office" in second.say.lower() or "oficina" in second.say.lower()


def test_stale_open_calls_close_as_missed(tmp_path):
    store = Store(tmp_path / "stale.db")
    now = datetime(2026, 10, 22, 15, 0, tzinfo=ZoneInfo("America/Chicago"))
    fresh = SessionState()
    stale = SessionState()
    store.create_call("fresh", "simulator", None, now - timedelta(minutes=5), fresh)
    store.create_call("old", "simulator", None, now - timedelta(minutes=45), stale)
    closed = store.expire_stale_calls(now)
    assert closed == 1
    rows = {call["id"]: call for call in store.list_calls()}
    assert rows["fresh"]["outcome"] is None
    assert rows["old"]["outcome"] == "missed"
    assert rows["old"]["phase"] == "closed"
