"""Round-6 classes: negated danger answers, dates, names, addresses, and routine jobs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.agent.calendar import MemoryCalendar
from app.agent.engine import Engine, SessionState
from app.agent.hazard import classify_emergency
from app.agent.nlu import extract_caller_name, extract_street, is_negated_danger
from app.agent.scheduling import available_slots, parse_preference
from app.config_loader import load_business
from app.main import create_app
from app.service import FixedClock
from app.settings import Settings
from app.voice.twilio import twilio_signature

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_business(ROOT / "config" / "business.yaml")
ZONE = ZoneInfo("America/Chicago")
THU = datetime(2026, 10, 22, 9, 0, tzinfo=ZONE)

NEGATED = [
    "Nobody is in danger",
    "Nobody's in danger",
    "This is not an emergency",
    "No one is hurt",
    "We are fine",
    "Everyone is safe",
    "Callback please",
    "Nothing is unsafe",
    "We aren't in danger",
    "Please call me back, nobody is hurt",
]
AFFIRMED = [
    "yes",
    "yes, call me back",
    "someone is hurt",
    "this is an emergency",
    "people are injured",
]


def _engine() -> Engine:
    return Engine(CONFIG, MemoryCalendar(), FixedClock(THU))


def _ready(phase: str) -> SessionState:
    return SessionState(
        phase=phase,
        intent="new_job",
        issue="Clogged drain",
        name="Sam Rivera",
        phone="5125550142",
        street="4410 Duval Street",
        address="4410 Duval Street, Austin 78751",
        zip="78751",
        city="Austin",
    )


def test_negated_danger_never_pages_and_a_yes_does():
    engine = _engine()
    for phrase in NEGATED:
        assert is_negated_danger(phrase) or "call" in phrase.lower()
        check = SessionState(phase="hazard_check", issue="odd smell")
        engine.handle(check, phrase)
        assert check.outcome != "escalated", phrase
        handoff = SessionState(phase="unclear_handoff", unclear_count=3)
        engine.handle(handoff, phrase)
        assert handoff.outcome != "escalated", phrase
    for phrase in AFFIRMED:
        check = SessionState(phase="hazard_check", issue="odd smell")
        engine.handle(check, phrase)
        assert check.outcome == "escalated", phrase
        handoff = SessionState(phase="unclear_handoff", unclear_count=3)
        engine.handle(handoff, phrase)
        assert handoff.outcome == "escalated", phrase


def test_a_vague_third_turn_asks_instead_of_paging():
    engine = _engine()
    state = SessionState()
    engine.handle(state, "asdf qwerty")
    second = engine.handle(state, "the water")
    assert state.outcome != "escalated"
    assert "danger" in second.say.lower()


def test_gas_smell_fire_and_fast_water_page_and_fees_do_not():
    gas, gas_label = classify_emergency("I caught a whiff of gas by the meter.")
    assert gas == "definite" and gas_label == "Gas"
    flames, flame_label = classify_emergency("There are flames on the outdoor compressor.")
    assert flames == "definite" and flame_label == "Electrical hazard"
    water, water_label = classify_emergency("Water is rising in the basement and I think it can wait.")
    assert water == "definite" and water_label == "Active water"
    fee, _ = classify_emergency("What is the weekend after-hours rate?")
    assert fee == "none"
    engine = _engine()
    state = SessionState()
    result = engine.handle(state, "What do you charge as an after-hours rate on a Saturday?")
    assert state.outcome != "escalated"
    assert state.intent == "quote"
    assert "price" in result.say.lower() or "$" in result.say


def test_a_gas_hookup_without_a_smell_can_be_booked():
    engine = _engine()
    state = SessionState()
    turns = [
        "Please hook up a gas dryer. There is no odor at all.",
        "Dana Brooks",
        "512-555-0191",
        "15 Cedar Avenue, Austin 78702",
        "the earliest you have",
        "yes",
    ]
    last = None
    for turn in turns:
        last = engine.handle(state, turn)
    assert state.outcome == "booked"
    assert last is not None
    assert "booked" in last.say.lower()


def test_a_brand_surname_is_accepted_and_the_name_question_stops():
    assert extract_caller_name(["Pat Rheem"], "name", "Pat Rheem") == "Pat Rheem"
    assert extract_caller_name(["Sam Lane"], "name", "Sam Lane") == "Sam Lane"
    engine = _engine()
    state = SessionState(phase="collect_name", intent="new_job", issue="Thermostat", asked_field="name")
    first = engine.handle(state, "water heater")
    assert state.name is None
    assert "name" in first.say.lower()
    second = engine.handle(state, "????")
    assert state.name
    assert state.name_confidence == "low"
    assert "name" not in second.say.lower() or "phone" in second.say.lower()


def test_a_temperature_is_not_an_address_and_is_not_read_on_the_emergency_line():
    assert extract_street("The house is 79 inside and the heat is out") is None
    assert extract_street("She is 80 years old and cold") is None
    engine = _engine()
    state = SessionState(address="79 Inside, Austin", street="79 Inside")
    result = engine.handle(state, "I smell gas by the furnace")
    assert state.outcome == "escalated"
    assert "79 Inside" not in result.say
    booking = SessionState(phase="collect_address", intent="new_job", issue="Thermostat", name="Ada Lane", phone="5125550100")
    heard = engine.handle(booking, "15 Cedar Avenue")
    assert booking.address_from_prompt is True
    assert "Cedar" in heard.say


def test_bare_ordinal_end_of_month_lunch_and_a_past_day():
    third = parse_preference("the 3rd", THU)
    assert third is not None and third.day is not None
    assert (third.day.month, third.day.day) == (11, 3)
    end = parse_preference("end of the month", THU)
    assert end is not None and end.day is not None and end.day_until is not None
    assert end.day.month == 10 and end.day.day == 28
    assert end.day_until.day == 30
    lunch = parse_preference("lunchtime", THU)
    assert lunch is not None and lunch.part == "lunch"
    slots, relaxed = available_slots(CONFIG, THU, [], preference=lunch, limit=3)
    assert slots and not relaxed
    assert all(11 <= slot.hour <= 13 for slot in slots)
    assert all(slot.hour != 7 for slot in slots)
    engine = _engine()
    state = _ready("offer")
    past = engine.handle(state, "the 21st")
    assert "November 21" in past.say
    assert "past my booking window" in past.say
    assert "I can book up to" in past.say
    assert state.outcome != "booked"
    assert state.offered == []
    unclear = engine.handle(_ready("offer"), "the 32nd")
    assert "Which day did you mean?" in unclear.say


def test_a_missed_transfer_without_a_webhook_does_not_promise_a_callback(tmp_path):
    settings = Settings(
        config_path=ROOT / "config" / "business.yaml",
        db_path=tmp_path / "miss.db",
        static_dir=None,
        seed_on_start=False,
        demo_mode=False,
        admin_token="desk-token",
        twilio_auth_token="testtoken123",
        public_base_url="https://desk.example.com",
    )
    with TestClient(create_app(settings)) as client:
        form = {"CallSid": "CA-miss", "DialCallStatus": "no-answer", "From": "+15125550177"}
        started = client.app.state.service.start("twilio", external_id="CA-miss")
        state = client.app.state.store.load_state(started["id"])
        state.hazard = "Gas"
        client.app.state.store.save_state(started["id"], state, False, None)
        dialed = client.post(
            "/api/voice/twilio/dial-status",
            data=form,
            headers={"X-Twilio-Signature": twilio_signature("https://desk.example.com/api/voice/twilio/dial-status", form, "testtoken123")},
        )
        assert dialed.status_code == 200
        body = dialed.text.lower()
        assert "call you back" not in body
        assert "logged" in body
        assert "911" in body
