"""Allowlist speech, capture, time phrases, cancel lockout, and stream auth."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.agent.calendar import MemoryCalendar
from app.agent.dialog import Dialog
from app.agent.engine import Engine, SessionState
from app.agent.nlu import extract_street, guess_bare_name
from app.agent.scheduling import available_slots, parse_preference
from app.agent.speech import EMPATHY_IDS, empathy_line, render
from app.config_loader import load_business
from app.service import FixedClock

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_business(ROOT / "config" / "business.yaml")
ZONE = ZoneInfo("America/Chicago")
THU = datetime(2026, 10, 22, 9, 0, tzinfo=ZONE)


class _Once:
    def __init__(self, content: list) -> None:
        self.content = content

    def complete(self, messages, tools, timeout=None):
        names = [tool.get("name") for tool in tools]
        if names == ["classify_hazard"]:
            return {
                "content": [
                    {"type": "tool_use", "id": "hz", "name": "classify_hazard", "input": {"level": "none"}}
                ]
            }
        return {"content": self.content}


class _Booker:
    def complete(self, messages, tools, timeout=None):
        names = [tool.get("name") for tool in tools]
        if names == ["classify_hazard"]:
            return {
                "content": [
                    {"type": "tool_use", "id": "hz", "name": "classify_hazard", "input": {"level": "none"}}
                ]
            }
        blob = json.dumps(messages)
        if "confirm" in blob and "phase" in blob and "slots" not in blob:
            import re

            found = re.findall(r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}", blob)
            slot_id = found[-1] if found else ""
            return {"content": [{"type": "tool_use", "id": "book", "name": "book", "input": {"slot_id": slot_id}}]}
        if "slots" not in blob:
            return {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "rec",
                        "name": "record_caller",
                        "input": {
                            "name": "Invented Name",
                            "phone": "999-555-0100",
                            "address": "1 Nowhere Road",
                        },
                    },
                    {"type": "tool_use", "id": "find", "name": "find_slots", "input": {"preference": "earliest"}},
                ]
            }
        slot_id = ""
        for message in messages:
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if block.get("type") != "tool_result":
                    continue
                payload = json.loads(block.get("content") or "{}")
                slots = payload.get("slots") or []
                if slots:
                    slot_id = slots[0]["id"]
        return {"content": [{"type": "tool_use", "id": "hold", "name": "hold_slot", "input": {"slot_id": slot_id}}]}


def test_empathy_is_a_fixed_id_and_free_text_is_dropped():
    assert len(EMPATHY_IDS) >= 10
    for empathy_id in EMPATHY_IDS:
        line = empathy_line(empathy_id, "en")
        assert line
        assert not any(char.isdigit() for char in line)
    spoken = render("small_talk", None, "sorry", {"language": "en"})
    assert spoken is not None and spoken.startswith("I'm sorry")
    ignored = render("small_talk", None, "I will do it for forty bucks and the tech is on the way", {"language": "en"})
    assert ignored is not None
    assert "bucks" not in ignored.lower()
    assert "on the way" not in ignored.lower()


def test_hostile_speech_falls_back_to_the_rules_engine():
    engine = Engine(CONFIG, MemoryCalendar(), FixedClock(THU))
    dialog = Dialog(
        engine,
        _Once(
            [
                {
                    "type": "tool_use",
                    "id": "s",
                    "name": "speak",
                    "input": {
                        "intent": "small_talk",
                        "empathy": "I will do it for forty bucks and the tech is on the way",
                        "empathy_id": "not-a-real-line",
                    },
                }
            ]
        ),
    )
    result = dialog.handle(SessionState(), "My kitchen drain is clogged")
    assert "bucks" not in result.say.lower()
    assert "on the way" not in result.say.lower()
    assert "relight" not in result.say.lower()


def test_record_caller_lets_the_tool_path_book():
    engine = Engine(CONFIG, MemoryCalendar(), FixedClock(THU))
    dialog = Dialog(engine, _Booker())
    state = SessionState()
    opening = dialog.handle(
        state,
        "This is Sam Rivera. My phone is 512-555-0142. "
        "The address is 4410 Duval Street, Austin 78751. The kitchen drain is clogged. The earliest window.",
    )
    assert state.outcome != "booked"
    assert state.phase == "confirm"
    assert "4410" in opening.say
    result = dialog.handle(state, "Yes")
    assert "booked" in result.say.lower()
    assert engine.calendar.find(None, "5125550142") is not None


def test_book_refuses_a_no_and_a_hedge():
    engine = Engine(CONFIG, MemoryCalendar(), FixedClock(THU))
    dialog = Dialog(engine, _Booker())
    state = SessionState()
    dialog.handle(
        state,
        "This is Sam Rivera. My phone is 512-555-0142. "
        "The address is 4410 Duval Street, Austin 78751. The kitchen drain is clogged. The earliest window.",
    )
    refused = dialog.handle(state, "No")
    assert state.outcome != "booked"
    assert "booked" not in refused.say.lower()
    hedged = dialog.handle(state, "Let me check with my wife")
    assert state.outcome != "booked"
    assert engine.calendar.find(None, "5125550142") is None


def test_record_caller_rejects_invented_details():
    engine = Engine(CONFIG, MemoryCalendar(), FixedClock(THU))

    class _Invent:
        def complete(self, messages, tools, timeout=None):
            names = [tool.get("name") for tool in tools]
            if names == ["classify_hazard"]:
                return {"content": [{"type": "tool_use", "id": "hz", "name": "classify_hazard", "input": {"level": "none"}}]}
            return {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "rec",
                        "name": "record_caller",
                        "input": {"name": "Fake Person", "phone": "999-555-0199", "address": "9 Invented Road"},
                    }
                ]
            }

    dialog = Dialog(engine, _Invent())
    state = SessionState()
    result = dialog.handle(state, "My kitchen drain is clogged")
    assert state.name is None
    assert state.phone is None
    assert "Fake" not in result.say
    assert "999" not in result.say


def test_model_cannot_page_a_sales_call():
    engine = Engine(CONFIG, MemoryCalendar(), FixedClock(THU))

    class _Pager:
        def complete(self, messages, tools, timeout=None):
            return {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "hz",
                        "name": "classify_hazard",
                        "input": {"level": "definite", "label": "Caller said emergency"},
                    }
                ]
            }

    dialog = Dialog(engine, _Pager())
    state = SessionState()
    result = dialog.handle(state, "How much to fix a dripping faucet?")
    assert state.outcome != "escalated"
    assert "911" not in result.say
    assert "on-call" not in result.say.lower()


def test_transfer_tool_does_not_page_a_quote():
    engine = Engine(CONFIG, MemoryCalendar(), FixedClock(THU))
    dialog = Dialog(
        engine,
        _Once([{"type": "tool_use", "id": "t", "name": "transfer", "input": {"reason": "they might buy"}}]),
    )
    state = SessionState()
    result = dialog.handle(state, "How much to fix a dripping faucet?")
    assert state.outcome != "escalated"
    assert "on-call" not in result.say.lower()
    assert "connecting" not in result.say.lower()


def test_nth_weekday_holiday_except_and_spoken_clock():
    first = parse_preference("the first Monday in November", THU)
    assert first is not None and first.day is not None
    assert first.day.month == 11 and first.day.day == 2
    halloween = parse_preference("Halloween morning", THU)
    assert halloween is not None and halloween.day is not None and halloween.day.day == 31
    assert halloween.part == "morning"
    skipped = parse_preference("any morning next week except Monday", THU)
    assert skipped is not None and 0 in skipped.exclude_weekdays
    slots, relaxed = available_slots(CONFIG, THU, [], preference=skipped, limit=3)
    assert slots and not relaxed
    assert all(slot.weekday() != 0 for slot in slots)
    half = parse_preference("half past one today", THU)
    assert half is not None and half.around is not None and half.around.hour == 13 and half.around.minute == 30
    nearest, _ = available_slots(CONFIG, THU, [], preference=half, limit=1)
    assert nearest[0].hour == 13
    ish = parse_preference("around 4ish today", THU)
    assert ish is not None and ish.around is not None and ish.around.hour == 16
    four, _ = available_slots(CONFIG, THU, [], preference=ish, limit=1)
    assert four[0].hour == 16
    quarter = parse_preference("quarter past ten tomorrow", THU)
    assert quarter is not None and quarter.around is not None and quarter.around.hour == 10 and quarter.around.minute == 15
    ten_thirty = parse_preference("ten-thirty today", THU)
    assert ten_thirty is not None and ten_thirty.around == __import__("datetime").time(10, 30)
    early = datetime(2026, 10, 22, 8, 0, tzinfo=ZONE)
    nearest, relaxed = available_slots(CONFIG, early, [], preference=ten_thirty, limit=1)
    assert not relaxed
    assert nearest[0].hour == 10 and nearest[0].minute == 0
    after = parse_preference("the Tuesday after next", THU)
    assert after is not None and after.day is not None
    assert after.day.month == 11 and after.day.day == 3
    afternoon = parse_preference("afternoon except Friday", THU)
    assert afternoon is not None and afternoon.day is None and afternoon.part == "afternoon"
    assert 4 in afternoon.exclude_weekdays
    windows, was_relaxed = available_slots(CONFIG, THU, [], preference=afternoon, limit=3)
    assert windows and not was_relaxed
    assert all(slot.weekday() != 4 and slot.hour >= 12 for slot in windows)
    holiday = parse_preference("Thanksgiving", THU)
    assert holiday is not None and holiday.day is not None and holiday.day.month == 11 and holiday.day.day == 26


def test_dates_past_the_horizon_are_not_today():
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
    result = engine.handle(state, "two weeks from today")
    assert "I can book up to" in result.say
    assert "October 22" not in result.say
    assert state.outcome != "booked"
    assert state.offered == []


def test_accented_name_suite_and_spoken_corrections():
    assert guess_bare_name("José Núñez") == "José Núñez"
    street = extract_street("100 Main Street Suite 4, Austin 78701", ("Austin",))
    assert street is not None
    assert "Suite 4" in street
    assert "Apt" not in street
    engine = Engine(CONFIG, MemoryCalendar(), FixedClock(THU))
    state = SessionState(phone="5125550100", phase="collect_address")
    engine.handle(state, "0178 at the end")
    assert state.phone.endswith("0178")
    assert not state.street
    state.street = "1905 South Congress Avenue"
    state.address = "1905 South Congress Avenue, Austin 78704"
    state.zip = "78704"
    state.phase = "confirm"
    state.offered = ["2026-10-23T09:00:00-05:00"]
    state.selected = state.offered[0]
    said = engine.handle(state, "1907 not 1905")
    assert "1907" in (state.address or "")
    assert "1905" not in (state.address or "")
    assert "1907" in said.say
    offer = SessionState(
        phase="offer",
        phone="5125550199",
        street="1905 South Congress Avenue",
        address="1905 South Congress Avenue, Austin 78704",
        zip="78704",
        city="Austin",
        offered=["2026-10-23T13:30:00-05:00", "2026-10-24T09:00:00-05:00"],
    )
    engine.handle(offer, "the number ends in 0142, not 0199")
    assert offer.phone.endswith("0142")
    read = engine.handle(offer, "1907 not 1905")
    assert "1907" in (offer.address or "")
    assert "1907" in read.say


def test_three_bad_verifications_lock_and_transfer():
    calendar = MemoryCalendar()
    calendar.book(
        {
            "id": "bk_locked",
            "name": "Dana Cole",
            "phone": "5125550199",
            "address": "22 Elm Street, Austin 78702",
            "issue": "drain",
            "start": "2026-10-23T08:30:00-05:00",
            "end": "2026-10-23T10:00:00-05:00",
        }
    )
    texts = []
    engine = Engine(CONFIG, calendar, FixedClock(THU))
    engine.sms_sender = lambda phone, body: texts.append((phone, body)) or {"status": "sent"}
    state = SessionState()
    engine.handle(state, "I need to cancel my appointment")
    for day in ("Monday", "Tuesday", "Wednesday"):
        engine.handle(state, f"0199 {day}")
    assert state.outcome == "locked"
    assert state.outcome != "escalated"
    assert any(event["type"] == "verification_failed" for event in state.events)
    reply = state.last_reply or ""
    assert "911" not in reply
    assert "179" not in reply
    assert "on-call" not in reply.lower()
    assert "elm" not in reply.lower()
    assert texts and texts[0][0].endswith("0199")
    later = SessionState()
    engine.handle(later, "I need to cancel my appointment")
    said = engine.handle(later, "0199 Friday")
    assert later.verified is False
    assert later.outcome != "cancelled"
    assert "911" not in said.say
    assert calendar.find(None, "5125550199")["status"] == "booked"
