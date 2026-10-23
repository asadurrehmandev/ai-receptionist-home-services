"""Round-5 failure classes: offline hazards, names, unclear calls, and fallbacks."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.agent.calendar import MemoryCalendar
from app.agent.dialog import Dialog
from app.agent.engine import Engine, SessionState
from app.agent.hazard import classify_emergency
from app.agent.nlu import extract_caller_name, guess_bare_name
from app.agent.scheduling import parse_preference
from app.config_loader import load_business
from app.main import _missed_guidance, create_app
from app.service import FixedClock
from app.settings import Settings
from app.voice.twilio import twilio_signature

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_business(ROOT / "config" / "business.yaml")
ZONE = ZoneInfo("America/Chicago")
THU = datetime(2026, 10, 22, 9, 0, tzinfo=ZONE)


def test_repaired_event_does_not_page_and_a_new_smell_does():
    quiet, _ = classify_emergency("The gas leak was repaired and there is no odor today.")
    assert quiet == "none"
    live, label = classify_emergency("They repaired a leak last month, but I smell gas right now.")
    assert live == "definite"
    assert label == "Gas"


def test_ceiling_water_sewage_alarm_and_scorch_page():
    water, water_label = classify_emergency("Water is coming through the bedroom ceiling.")
    assert water == "definite" and water_label == "Active water"
    sewage, sewage_label = classify_emergency("Sewer water is rising out of the floor drain.")
    assert sewage == "definite" and sewage_label == "Active water"
    alarm, alarm_label = classify_emergency("The upstairs alarm reads 200 and will not stop.")
    assert alarm == "definite" and alarm_label == "Carbon monoxide"
    hot, hot_label = classify_emergency("The wall behind the furnace is scorched and too hot to touch.")
    assert hot == "definite" and hot_label == "Electrical hazard"


def test_negation_and_a_green_light_stay_routine():
    sparks, _ = classify_emergency("The switch is loose and there are no sparks.")
    assert sparks == "none"
    green, _ = classify_emergency("The detector is showing a green light and I want a test.")
    assert green == "none"


def test_a_damp_spot_asks_and_an_infant_without_heat_pages():
    damp, _ = classify_emergency("There is a damp spot on the ceiling and it is not moving.")
    assert damp == "ask"
    infant, label = classify_emergency("There is no heat and an infant is in the bedroom.")
    assert infant == "definite" and label == "Unsafe indoor temperature"


def test_embedder_failure_asks_instead_of_clearing_the_call(tmp_path):
    import app.agent.hazard_semantic as semantic

    saved_model, saved_flag = semantic._model, semantic._load_failed
    semantic._model = None
    semantic._load_failed = True
    try:
        level, label = classify_emergency("there is a weird smell in the closet")
        assert level == "ask"
        assert label == "Hazard model unavailable"
        settings = Settings(
            config_path=ROOT / "config" / "business.yaml",
            db_path=tmp_path / "down.db",
            static_dir=None,
            seed_on_start=False,
        )
        with TestClient(create_app(settings)) as client:
            health = client.get("/api/health")
            assert health.status_code == 503
            assert health.json()["semantic_ready"] is False
    finally:
        semantic._model = saved_model
        semantic._load_failed = saved_flag


def test_name_comes_from_the_answer_not_the_street_or_the_brand():
    blocked = guess_bare_name("The Bradford White at 14 Koenig Lane is leaking.")
    assert blocked is None
    asked = extract_caller_name(
        ["The Bradford White at 14 Koenig Lane is leaking.", "Priya Nair"],
        "name",
        "Priya Nair",
    )
    assert asked == "Priya Nair"
    introduced = extract_caller_name(
        ["This is Sam Rivera. My phone is 512-555-0142. 4410 Duval Street, Austin 78751."],
        None,
        "This is Sam Rivera. My phone is 512-555-0142. 4410 Duval Street, Austin 78751.",
    )
    assert introduced == "Sam Rivera"
    corrected = extract_caller_name(
        ["This is Sam Rivera.", "actually it's Maria Lopez"],
        None,
        "actually it's Maria Lopez",
    )
    assert corrected == "Maria Lopez"


class _NameModel:
    def complete(self, messages, tools, timeout=None):
        names = [tool.get("name") for tool in tools]
        if names == ["classify_hazard"]:
            return {"content": [{"type": "tool_use", "id": "hz", "name": "classify_hazard", "input": {"level": "none"}}]}
        blob = ""
        for message in messages:
            blob += str(message.get("content"))
        if "Priya Nair" in blob or "Maria Lopez" in blob or "Dana Cho" in blob:
            return {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "rec",
                        "name": "record_caller",
                        "input": {"name": "Wrong Name", "phone": "999-555-0100", "address": "1 Nowhere Road"},
                    }
                ]
            }
        return {
            "content": [
                {
                    "type": "tool_use",
                    "id": "ask",
                    "name": "speak",
                    "input": {"intent": "ask_field", "field": "name", "empathy_id": "of_course"},
                }
            ]
        }


def test_tool_path_keeps_the_callers_name():
    engine = Engine(CONFIG, MemoryCalendar(), FixedClock(THU))
    dialog = Dialog(engine, _NameModel())
    state = SessionState()
    dialog.handle(state, "The Bradford White at 14 Koenig Lane needs a flush.")
    assert state.asked_field == "name"
    dialog.handle(state, "Priya Nair")
    assert state.name == "Priya Nair"
    dialog.handle(state, "actually it's Maria Lopez")
    assert state.name == "Maria Lopez"


def test_unclear_menu_stops_after_two_tries_and_still_checks_hazards():
    engine = Engine(CONFIG, MemoryCalendar(), FixedClock(THU))
    state = SessionState()
    first = engine.handle(state, "asdf qwerty")
    assert "what's going on" in first.say.lower()
    fresh = SessionState()
    engine.handle(fresh, "asdf qwerty")
    smelled = engine.handle(fresh, "I smell gas by the furnace")
    assert fresh.outcome == "escalated"
    loop = SessionState()
    engine.handle(loop, "asdf qwerty")
    second = engine.handle(loop, "blah blah blah")
    assert "danger" in second.say.lower()
    assert "what's going on" not in second.say.lower()
    assert loop.phase == "unclear_handoff"
    callback = engine.handle(loop, "a person please")
    assert loop.outcome == "callback"
    assert callback.events
    assert all(event["type"] != "transfer" for event in callback.events)
    assert "911" in callback.say


def test_mid_november_is_not_booked_as_today():
    parsed = parse_preference("mid November", THU)
    assert parsed is not None and parsed.day is not None
    assert parsed.day.month == 11 and parsed.day.day == 15
    engine = Engine(CONFIG, MemoryCalendar(), FixedClock(THU))
    state = SessionState(
        phase="offer",
        name="Sam Rivera",
        phone="5125550142",
        street="4410 Duval Street",
        address="4410 Duval Street, Austin 78751",
        zip="78751",
        city="Austin",
        issue="Clogged drain",
        offered=["2026-10-23T09:00:00-05:00"],
    )
    result = engine.handle(state, "mid November")
    assert "I can book up to" in result.say
    assert "October 22" not in result.say
    assert state.offered == []


def test_no_heat_miss_does_not_use_the_gas_script(tmp_path):
    guidance = _missed_guidance("Unsafe indoor temperature", False)
    assert "warm" in guidance.lower()
    assert "smell gas" not in guidance.lower()
    assert "911" in guidance
    gas = _missed_guidance("Gas", False)
    assert "smell gas" in gas.lower()
    settings = Settings(
        config_path=ROOT / "config" / "business.yaml",
        db_path=tmp_path / "heat.db",
        static_dir=None,
        seed_on_start=False,
        demo_mode=True,
        twilio_auth_token="testtoken123",
        public_base_url="https://demo.example.com",
    )
    with TestClient(create_app(settings)) as client:
        form = {"CallSid": "CA-heat", "DialCallStatus": "no-answer", "From": "+15125550177"}
        # Plant the hazard by starting a call the detector will escalate, then mark the sid.
        from app.service import ReceptionService
        from app.store import Store

        store = client.app.state.store
        assert isinstance(store, Store)
        started = client.app.state.service
        assert isinstance(started, ReceptionService)
        opened = started.start("twilio", external_id="CA-heat")
        state = store.load_state(opened["id"])
        state.hazard = "Unsafe indoor temperature"
        store.save_state(opened["id"], state, False, None)
        dialed = client.post(
            "/api/voice/twilio/dial-status",
            data=form,
            headers={"X-Twilio-Signature": twilio_signature("https://demo.example.com/api/voice/twilio/dial-status", form, "testtoken123")},
        )
        assert dialed.status_code == 200
        body = dialed.text.lower()
        assert "warm" in body
        assert "smell gas" not in body
        assert "call you back" in body
        leads = client.get("/api/leads").json()["leads"]
        assert leads[0]["status"] == "missed_transfer"
        hooks = client.get("/api/events").json()["events"]
        assert any(event["payload"].get("event") == "call.transfer_missed" for event in hooks)


def test_tts_failure_during_an_emergency_dials(tmp_path):
    from app.service import ReceptionService
    from app.settings import Settings as DeskSettings
    from app.store import Store
    from app.voice.stream import MediaBridge

    settings = DeskSettings(
        config_path=ROOT / "config" / "business.yaml",
        db_path=tmp_path / "tts.db",
        static_dir=None,
        seed_on_start=False,
    )
    store = Store(settings.db_path)
    service = ReceptionService(CONFIG, store, settings, FixedClock(THU))
    updates = []

    def boom(_text: str) -> bytes:
        raise RuntimeError("tts down")

    bridge = MediaBridge(
        service,
        synthesize=boom,
        updater=lambda sid, twiml: updates.append(twiml),
        on_call_phone=CONFIG.on_call_phone,
        caller_id=CONFIG.phone_e164,
        dial_action="https://demo.example.com/api/voice/twilio/dial-status",
    )
    bridge.handle({"event": "start", "start": {"streamSid": "MZ", "callSid": "CA-tts"}})
    bridge.apply_transcript("I smell gas by the furnace")
    assert updates
    assert "<Dial" in updates[-1]
    assert "<Hangup" not in updates[-1]
    store.close()
