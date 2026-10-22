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
from app.agent.speech import empathy_ok, render
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
        if "slots" not in blob:
            return {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "rec",
                        "name": "record_caller",
                        "input": {
                            "name": "Sam Rivera",
                            "phone": "512-555-0142",
                            "address": "4410 Duval Street, Austin 78751",
                            "unit": "",
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
        return {
            "content": [
                {"type": "tool_use", "id": "hold", "name": "hold_slot", "input": {"slot_id": slot_id}},
                {"type": "tool_use", "id": "book", "name": "book", "input": {"slot_id": slot_id}},
            ]
        }


def test_empathy_rejects_prices_times_and_promises():
    for line in (
        "I can do forty bucks",
        "Come by half past one",
        "This one is on the house",
        "The tech is on the way",
        "You can relight it yourself",
    ):
        assert empathy_ok(line) is False
    assert empathy_ok("Sorry you are dealing with that.") is True
    assert render("small_talk", None, "forty bucks", {"language": "en"}) is None


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
                    "input": {"intent": "small_talk", "empathy": "I will do it for forty bucks and the tech is on the way"},
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
    result = dialog.handle(SessionState(), "My kitchen drain is clogged and I need someone soon")
    assert "booked" in result.say.lower()
    assert "4410" in result.say
    assert engine.calendar.find(None, "5125550142") is not None


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


def test_three_bad_verifications_lock_and_transfer():
    engine = Engine(CONFIG, MemoryCalendar(), FixedClock(THU))
    state = SessionState()
    engine.handle(state, "I need to cancel my appointment")
    for day in ("Monday", "Tuesday", "Wednesday"):
        engine.handle(state, f"0199 {day}")
    assert state.outcome == "escalated"
    assert any(event["type"] == "verification_failed" for event in state.events)
    assert "911" in (state.last_reply or "")
