"""Round 7: safety-first answers, plain jobs, Avenue B, and the frozen file."""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.agent.calendar import MemoryCalendar
from app.agent.engine import Engine, SessionState
from app.agent.hazard import classify_emergency
from app.agent.hazard_nli import nli_opinion
from app.agent.nlu import extract_street, safety_decision
from app.config_loader import load_business
from app.main import create_app
from app.service import FixedClock
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.round7 import score_round7
from evals.round7_set import ROUND7

CONFIG = load_business(ROOT / "config" / "business.yaml")
ZONE = ZoneInfo("America/Chicago")
THU = datetime(2026, 10, 22, 9, 0, tzinfo=ZONE)

# Categories, not a reviewer's sentences. Each one is harm, a hedge, or urgency.
HARMS = [
    "I feel dizzy",
    "she is lightheaded",
    "he fainted",
    "she passed out",
    "he collapsed",
    "I can't breathe",
    "there is trouble breathing",
    "the child is wheezing",
    "this is an asthma attack",
    "she is throwing up",
    "he is vomiting",
    "I am nauseous",
    "she seems confused",
    "he is hard to wake",
    "she won't wake up",
    "he is unresponsive",
    "I have a bad headache",
    "there is chest pain",
    "she fell and can't get up",
    "I see smoke",
    "there is a fire",
    "the outlet is throwing sparks",
    "it is getting worse",
    "it is spreading",
    "the water is coming faster",
    "please hurry",
    "wait",
    "I think so",
    "maybe",
    "I guess",
    "I don't know",
    "uh huh",
]
CLEARS = [
    "No",
    "Nope",
    "Nah",
    "Not an emergency",
    "We're fine",
    "Everybody is safe",
    "No one is injured",
    "Nobody is hurt",
    "It is not an emergency",
    "We are okay",
]


def _engine() -> Engine:
    return Engine(CONFIG, MemoryCalendar(), FixedClock(THU))


def test_harm_answers_page_and_clean_nos_do_not():
    assert len(HARMS) >= 30
    assert len(CLEARS) >= 10
    engine = _engine()
    for phrase in HARMS:
        for spoken in (phrase, f"No, {phrase}"):
            assert safety_decision(spoken) == "page", spoken
            for phase in ("hazard_check", "unclear_handoff"):
                state = SessionState(phase=phase, issue="odd smell")
                engine.handle(state, spoken)
                assert state.outcome == "escalated", (phase, spoken)
    for phrase in CLEARS:
        assert safety_decision(phrase) == "clear", phrase
        check = SessionState(phase="hazard_check", issue="odd smell")
        engine.handle(check, phrase)
        assert check.outcome != "escalated", phrase
        handoff = SessionState(phase="unclear_handoff", unclear_count=3)
        engine.handle(handoff, phrase)
        assert handoff.outcome != "escalated", phrase
    both = SessionState(phase="hazard_check")
    engine.handle(both, "No, but I can't breathe")
    assert both.outcome == "escalated"


def test_a_spigot_and_low_pressure_book_without_a_danger_question():
    engine = _engine()
    for line in (
        "Can you install an outdoor spigot on the side of the house?",
        "The shower pressure is low and I would like it checked.",
        "Please replace the hose bib. Water pressure is weak.",
    ):
        state = SessionState()
        heard = engine.handle(state, line)
        assert state.outcome != "escalated", line
        assert state.phase != "hazard_check", line
        assert "danger" not in heard.say.lower(), line
        assert "name" in heard.say.lower(), line


def test_avenue_b_keeps_the_letter_and_suite_stays_a_unit():
    assert extract_street("1200 Avenue B, Austin 78702", ("Austin",), answering=True) == "1200 Avenue B"
    assert extract_street("1200 Avenue B") == "1200 Avenue B"
    suite = extract_street("100 Main Street Suite 4")
    assert suite is not None
    assert suite.startswith("100 Main Street")
    assert "Suite 4" in suite


def test_past_and_hypothetical_hazards_do_not_page_and_a_present_smell_does():
    cost, _ = classify_emergency("What would a gas leak cost to repair if we ever had one?")
    assert cost == "none"
    past, _ = classify_emergency("The leak was repaired last week. Can you reconnect the water heater?")
    assert past == "none"
    unsure, _ = classify_emergency("I am not sure the old leak is really gone.")
    assert unsure == "ask"
    now, label = classify_emergency("The repair was finished last month, but I smell it again right now.")
    assert now == "definite" and label == "Gas"


def test_round7_file_stays_frozen_and_matches_the_post_tune_score():
    assert len(ROUND7) == 59
    assert sum(1 for label, _text in ROUND7 if label == "transfer") == 35
    assert sum(1 for label, _text in ROUND7 if label == "routine") == 20
    report = score_round7()
    assert report["counts"]["transfer"] == [35, 35]
    assert report["counts"]["ask"] == [4, 4]
    assert report["counts"]["routine"] == [20, 20]
    assert report["false_pages"] == 0


def test_nli_scores_a_short_turn_under_300_ms():
    nli_opinion("warm the offline safety classifier before the timer")
    samples = []
    for _ in range(5):
        started = time.perf_counter()
        nli_opinion("The kitchen faucet has been dripping since Monday and needs a washer.")
        samples.append((time.perf_counter() - started) * 1000)
    median = sorted(samples)[len(samples) // 2]
    assert median < 300, median


def test_a_missing_nli_model_stays_up_and_does_not_clear_gas(tmp_path):
    import app.agent.hazard_nli as nli

    saved = (nli._session, nli._tokenizer, nli._load_failed)
    nli._session = None
    nli._tokenizer = None
    nli._load_failed = True
    try:
        settings = Settings(
            config_path=ROOT / "config" / "business.yaml",
            db_path=tmp_path / "nli-down.db",
            static_dir=None,
            seed_on_start=True,
            demo_mode=True,
        )
        with TestClient(create_app(settings)) as client:
            health = client.get("/api/health")
            assert health.status_code == 503
            body = health.json()
            assert body["ok"] is False
            assert body["nli_ready"] is False
            service = client.app.state.service
            gas = service.start("simulator")
            paged = service.turn(gas["id"], "I smell gas in the kitchen")
            assert paged["outcome"] == "escalated"
            job = service.start("simulator")
            heard = service.turn(job["id"], "Can you install an outdoor spigot on the south wall?")
            assert heard["outcome"] != "escalated"
    finally:
        nli._session, nli._tokenizer, nli._load_failed = saved
