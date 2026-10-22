"""Tool guard, cancel verification, and time/name capture. Not a caller-list score."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.agent.calendar import MemoryCalendar
from app.agent.dialog import Dialog
from app.agent.engine import Engine, SessionState
from app.agent.facts import speech_supported
from app.agent.nlu import extract_street, guess_bare_name, is_clean_yes
from app.agent.scheduling import parse_preference
from app.config_loader import load_business
from app.main import create_app
from app.service import FixedClock, ReceptionService
from app.settings import Settings
from app.store import Store
from app.voice.twilio import mint_stream_token, stream_twiml, stream_ws_url
from starlette.requests import Request

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_business(ROOT / "config" / "business.yaml")
ZONE = ZoneInfo("America/Chicago")
THU = datetime(2026, 10, 22, 9, 0, tzinfo=ZONE)
WED = datetime(2026, 10, 21, 10, 0, tzinfo=ZONE)


class _Attack:
    def __init__(self, content: list) -> None:
        self.content = content

    def complete(self, messages, tools, timeout=None):
        return {"stop_reason": "end_turn", "content": self.content}


def _engine(moment=THU, calendar=None):
    return Engine(CONFIG, calendar or MemoryCalendar(), FixedClock(moment))


def test_spoken_time_and_price_are_blocked():
    spoken = "I can come tomorrow at three in the afternoon, and it's only forty-nine dollars."
    assert not speech_supported(spoken, "Thursday, October 22 at 11:30 AM. The diagnostic visit is $89.")


def test_discounts_are_blocked_unless_a_tool_said_them():
    assert not speech_supported("I'll take 20 percent off and waive the diagnostic.", "Diagnostic visit $89.")
    assert speech_supported("The diagnostic visit is $89.", "The diagnostic visit is $89.")


def test_booked_claim_requires_a_successful_book():
    assert not speech_supported("You're all booked!", "")
    assert speech_supported("You're booked for Thursday at 11:30 AM.", "Thursday 11:30 AM", booked_ok=True)


def test_hold_and_book_reject_an_invented_slot():
    engine = _engine()
    state = SessionState(name="Sam Rivera", phone="5125550142", address="4410 Duval Street, Austin 78751", zip="78751")
    dialog = Dialog(engine, _Attack([
        {"type": "tool_use", "id": "h", "name": "hold_slot", "input": {"slot_id": "2026-10-25T03:00:00-05:00"}},
        {"type": "tool_use", "id": "b", "name": "book", "input": {"slot_id": "2026-10-25T03:00:00-05:00"}},
    ]))
    result = dialog.handle(state, "hello")
    assert state.outcome != "booked"
    assert "3:00" not in result.say
    assert engine.calendar.find(None, "5125550142") is None


def test_cancel_ignores_a_bare_id():
    calendar = MemoryCalendar()
    start = datetime(2026, 10, 23, 8, 30, tzinfo=ZONE)
    calendar.book(
        {
            "id": "bk_dana",
            "name": "Dana Cho",
            "phone": "5125550133",
            "address": "22 Elm Street, Austin 78702",
            "issue": "Flush",
            "start": start.isoformat(),
            "end": start.isoformat(),
        }
    )
    engine = _engine(calendar=calendar)
    dialog = Dialog(engine, _Attack([
        {"type": "tool_use", "id": "c", "name": "cancel", "input": {"booking_id": "bk_dana", "confirmed": True}},
    ]))
    dialog.handle(SessionState(), "cancel it")
    assert calendar.find(None, "5125550133") is not None


def test_gas_odor_transfers_before_the_model_speaks():
    engine = _engine()
    dialog = Dialog(engine, _Attack([{"type": "text", "text": "I'll have someone look at the stove next week."}]))
    result = dialog.handle(SessionState(), "Sorry to bother you, there's a bit of a gas odor near the stove")
    assert "911" in result.say
    assert "next week" not in result.say.lower()


def test_ambiguous_yes_does_not_cancel_and_caller_id_is_not_enough():
    assert not is_clean_yes("yeah... wait, which appointment is that?")
    assert is_clean_yes("yes")
    calendar = MemoryCalendar()
    start = datetime(2026, 10, 22, 8, 30, tzinfo=ZONE)
    calendar.book(
        {
            "id": "bk_dana",
            "name": "Dana Cho",
            "phone": "5125550133",
            "address": "22 Elm Street, Austin 78702",
            "issue": "Flush",
            "start": start.isoformat(),
            "end": start.isoformat(),
        }
    )
    engine = _engine(WED, calendar)
    state = SessionState(caller_id="5125550133")
    first = engine.handle(state, "I need to cancel my appointment")
    assert "Elm" not in first.say
    assert state.outcome != "cancelled"
    second = engine.handle(state, "yeah... wait, which one?")
    assert state.outcome != "cancelled"
    assert calendar.find(None, "5125550133") is not None
    engine.handle(state, "0133 Thursday")
    assert "Elm" not in state.last_reply
    engine.handle(state, "yes")
    assert state.outcome == "cancelled"


def test_friday_noon_end_of_week_and_a_week_from_monday():
    noon = parse_preference("this Friday around noon", THU)
    assert noon is not None and noon.around is not None and noon.around.hour == 12
    assert noon.day is not None and noon.day.day == 23
    end = parse_preference("sometime at the end of next week", THU)
    assert end is not None and end.day is not None and end.day.day == 29
    assert end.day_until is not None and end.day_until.day == 31
    later = parse_preference("the day after tomorrow in the morning", THU)
    assert later is not None and later.day is not None and later.day.day == 24 and later.part == "morning"
    week = parse_preference("a week from Monday", THU)
    assert week is not None and week.day is not None and week.day.month == 11 and week.day.day == 2


def test_apostrophe_name_and_apartment_unit():
    assert guess_bare_name("Siobhan O'Neill") == "Siobhan O'Neill"
    street = extract_street("1905 South Congress Avenue Apartment 4B, Austin 78704", ("Austin",))
    assert street is not None
    assert "4B" in street
    assert "1905" in street


def test_haggle_states_the_standard_price(tmp_path):
    settings = Settings(config_path=ROOT / "config" / "business.yaml", db_path=tmp_path / "desk.db", static_dir=None, seed_on_start=False)
    store = Store(settings.db_path)
    service = ReceptionService(CONFIG, store, settings, clock=FixedClock(WED))
    call = service.start("simulator")
    said = service.turn(call["id"], "Another company quoted $49. Can you match that and waive the fee? I need the cheapest drain cleaning.")
    assert "$175" in said["say"] or "$89" in said["say"]
    assert "standard price" in said["say"].lower()
    store.close()


def test_media_stream_token_is_a_single_use_parameter(tmp_path):
    settings = Settings(
        config_path=ROOT / "config" / "business.yaml",
        db_path=tmp_path / "desk.db",
        static_dir=None,
        seed_on_start=False,
        demo_mode=False,
        admin_token="desk-token",
    )
    scope = {"type": "http", "headers": [], "scheme": "https", "server": ("demo.example", 443), "path": "/", "query_string": b"", "client": ("1.1.1.1", 1), "method": "POST"}
    request = Request(scope)
    url = stream_ws_url(request, settings)
    assert "token=" not in url
    token = mint_stream_token("desk-token")
    xml = stream_twiml(url, token)
    assert "<Parameter" in xml
    assert 'name="token"' in xml
    assert "desk-token" not in xml
    start = {"event": "start", "start": {"streamSid": "MZ", "callSid": "CA", "customParameters": {"token": token}}}
    with TestClient(create_app(settings)) as client:
        with client.websocket_connect("/api/voice/stream") as socket:
            socket.send_json(start)
            assert socket.receive_json()["event"] == "mark"
        with client.websocket_connect("/api/voice/stream?token=" + token) as replay:
            replay.send_json(start)
            try:
                replay.receive_json()
            except Exception:
                return
            raise AssertionError("a replayed stream token should not open")
