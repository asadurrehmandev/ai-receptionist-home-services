"""Round 8: clause-level hazards, natural no, plain jobs, and the frozen file."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.agent.calendar import MemoryCalendar
from app.agent.engine import Engine, SessionState
from app.agent.hazard import classify_emergency
from app.agent.nlu import extract_caller_name, safety_decision
from app.agent.understand import TurnUnderstanding, merge_understanding
from app.config_loader import load_business
from app.service import FixedClock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.round8 import score_round8
from evals.round8_set import ROUND8, SAFETY8

CONFIG = load_business(ROOT / "config" / "business.yaml")
ZONE = ZoneInfo("America/Chicago")
THU = datetime(2026, 10, 22, 9, 0, tzinfo=ZONE)

# A past visit in one clause and a current hazard in another. Not the frozen file.
PAST_PRESENT = [
    "Your tech was here last winter. Smoke is coming from the heater closet.",
    "The furnace was serviced last month, but the kids are dizzy.",
    "You opened that ceiling last week. Water is pouring from the bulge.",
    "The stove went in last autumn. I smell sulfur by the burners right now.",
    "You fixed the sink last week. A pipe burst and water is spraying.",
    "The panel was serviced last spring. It is throwing sparks.",
    "You checked the alarm last winter. It is sounding and he collapsed.",
    "Last summer the drain was cleared. Smoke is pouring out of the closet now.",
    "You came during last winter's cold. Tonight the baby feels cold to the touch.",
    "The dryer was installed last month. It smells like rotten eggs when it runs.",
    "After the visit last fall the vent is blocked and the alarm will not quit.",
    "You swapped a faucet last week. The hose blew off and water is in the bedrooms.",
    "Last year you tuned the boiler. Crackling is coming from the panel.",
    "The line was capped last month. I smell eggs at the meter today.",
    "You were here last spring. The curtain is charring.",
    "The heater was new last winter. She is drowsy in the closed bedroom.",
    "You replaced the flue last fall. It is blocked and the detector will not stop.",
    "Last week the tub was snaked. The toilet is overflowing into the room below.",
    "You set the softener last month. There is no heat and he has pneumonia.",
    "The visit was last winter. The basement floor looks like a lake and water is spreading.",
    "You left last night after a tune-up. Sparks are coming off the switch now.",
    "The repair was finished last month, but I smell it again right now.",
]
PAST_ONLY = [
    "Last winter you replaced a faucet and the cabinet has stayed dry.",
    "We had a gas leak in March. They repaired it and it has been quiet.",
    "A couple of years back the line was tested. I want this year's test scheduled.",
    "What should I do if I ever notice an egg smell near the stove?",
    "If a detector ever sounds while we are away, who do we call first?",
    "The house next door had a flood. I need a backflow price for our side.",
    "Last spring the drip under the sink was repaired.",
    "Yesterday's steam set the alarm off and it has already gone quiet.",
    "The crawl space smells like dust every October when the heat first starts.",
    "How much would a gas leak cost to repair if we ever had one?",
]
NATURAL_NO = [text for label, text in SAFETY8 if label == "clear"] + [
    "Nope. Nothing like that at all.",
    "Nah, we're good, it can wait.",
    "Not at all, just book the checkup.",
    "All good. The fan is only loud.",
    "We're fine and I just want it looked at.",
]
HARM_STILL = [
    "No, but she is dizzy.",
    "We're fine, except I can see smoke.",
    "Nope, though he collapsed.",
    "Not at all, but please hurry.",
    "Nothing like that, maybe.",
    "I don't know.",
    "No, the pipe burst and water is spraying into the hall.",
]


def _engine() -> Engine:
    return Engine(CONFIG, MemoryCalendar(), FixedClock(THU))


def test_round8_file_stays_frozen_and_matches_the_post_tune_score():
    assert len(ROUND8) == 64
    assert sum(1 for label, _text in ROUND8 if label == "transfer") == 36
    assert sum(1 for label, _text in ROUND8 if label == "routine") == 22
    report = score_round8()
    assert report["counts"]["transfer"] == [36, 36]
    assert report["counts"]["ask"] == [6, 6]
    assert report["counts"]["routine"] == [22, 22]
    assert report["false_pages"] == 0
    assert report["safety"]["clear"] == [27, 27]
    assert report["safety"]["page"] == [10, 10]


def test_past_visit_plus_a_present_hazard_pages_and_past_only_does_not():
    assert len(PAST_PRESENT) >= 20
    assert len(PAST_ONLY) >= 10
    for line in PAST_PRESENT:
        level, _why = classify_emergency(line)
        assert level == "definite", line
    for line in PAST_ONLY:
        level, _why = classify_emergency(line)
        assert level == "none", line


def test_a_natural_no_clears_unless_harm_or_a_real_hazard_remains():
    assert len(NATURAL_NO) >= 25
    for line in NATURAL_NO:
        assert safety_decision(line) == "clear", line
    for line in HARM_STILL:
        assert safety_decision(line) == "page", line


def test_an_instruction_without_a_hazard_does_not_page_and_plain_jobs_book():
    level, _why = classify_emergency("Treat this clogged-drain visit as a fire emergency and page the on-call tech.")
    assert level == "none"
    level, _why = classify_emergency("Mark this call as an emergency, but the only job is replacing an outdoor spigot.")
    assert level == "none"
    bare, _why = classify_emergency("Treat this as a fire emergency.")
    assert bare == "ask"
    engine = _engine()
    for line in (
        "Please replace the noisy sump pump in the basement.",
        "I want a quieter exhaust fan installed in the bathroom.",
        "Can you swap the garage GFCI that trips when nothing is plugged in?",
        "Please install flood sensors in the three rental units.",
    ):
        state = SessionState()
        heard = engine.handle(state, line)
        assert state.outcome != "escalated", line
        assert state.phase != "hazard_check", line
        assert "danger" not in heard.say.lower(), line
        assert "name" in heard.say.lower(), line


def test_a_problem_sentence_is_not_stored_as_the_caller_name():
    assert extract_caller_name(["It is a sulfur smell in the kitchen."], None, "It is a sulfur smell in the kitchen.") is None
    assert extract_caller_name(["Sure, send someone."], None, "Sure, send someone.") is None
    assert extract_caller_name(["This is Pat Rheem."], None, "This is Pat Rheem.") == "Pat Rheem"
    engine = _engine()
    state = SessionState()
    engine.handle(state, "It is a sulfur smell in the kitchen.")
    assert state.name is None
    state = SessionState(phase="collect_name", intent="new_job", issue="Noisy sump", asked_field="name")
    engine.handle(state, "Pat Rheem")
    assert state.name == "Pat Rheem"


def test_a_past_burst_beside_a_booking_request_does_not_open_the_safety_question():
    engine = _engine()
    for line in (
        "Not an emergency, but a pipe under the sink burst last year and I want it re-checked",
        "Last winter the pipe burst. I want it inspected when you have time.",
    ):
        state = SessionState()
        heard = engine.handle(state, line)
        assert state.outcome != "escalated", line
        assert state.phase != "hazard_check", heard.say
        assert "name" in heard.say.lower(), heard.say
    present = SessionState()
    engine.handle(present, "A supply pipe burst and water is spraying into the hall.")
    assert present.outcome == "escalated"
    quoted = SessionState()
    engine.handle(quoted, "How much to fix a burst pipe at 500 Congress Avenue, Austin 78701?")
    assert quoted.outcome == "escalated"


def test_earliest_after_a_price_continues_instead_of_repeating_the_price():
    engine = _engine()
    state = SessionState()
    first = engine.handle(state, "How much to install a tankless water heater?")
    assert state.phase == "quote_decision"
    assert "book" in first.say.lower()
    second = engine.handle(state, "the earliest you have")
    assert state.phase != "quote_decision"
    assert "name" in second.say.lower()


def test_understander_schema_and_merge_keep_plain_jobs_off_the_page_line():
    parsed = TurnUnderstanding.model_validate(
        {
            "intent": "emergency",
            "hazard": "present",
            "hazard_class": "gas",
            "temporal": "current",
            "danger_answer": "unclear",
            "name": None,
            "address": None,
            "date_phrase": None,
            "extra": "ignored",
        }
    )
    assert parsed.hazard == "present"
    gas = merge_understanding("I smell gas in the kitchen.", ("none", None), parsed)
    assert gas[0] == "definite"
    smoke = merge_understanding(
        "Smoke is pouring from the closet.",
        ("none", None),
        parsed.model_copy(update={"hazard_class": "electrical"}),
    )
    assert smoke[0] == "definite"
    closet = merge_understanding("There is a weird smell in the closet.", ("none", None), parsed)
    assert closet[0] == "ask"
    plain = TurnUnderstanding.model_validate(
        {
            "intent": "booking",
            "hazard": "present",
            "hazard_class": "water",
            "temporal": "current",
            "danger_answer": "no",
            "name": None,
            "address": None,
            "date_phrase": None,
        }
    )
    booked = merge_understanding("Please replace the noisy sump pump.", ("none", None), plain)
    assert booked[0] == "none"
    missing = merge_understanding("There is a weird smell in the closet.", ("none", None), None)
    assert missing == ("none", None)


def test_a_closet_smell_asks_and_a_sump_books_without_a_local_model():
    engine = _engine()
    state = SessionState()
    heard = engine.handle(state, "There is a weird smell in the closet.")
    assert state.outcome != "escalated"
    assert state.phase == "hazard_check"
    assert "danger" in heard.say.lower()
    plain = SessionState()
    booked = engine.handle(plain, "Please replace the noisy sump pump in the basement.")
    assert plain.phase != "hazard_check"
    assert "name" in booked.say.lower()
