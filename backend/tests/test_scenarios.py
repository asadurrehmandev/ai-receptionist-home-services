"""Caller scenarios for the rule-based receptionist."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.agent.calendar import MemoryCalendar
from app.agent.engine import Engine, SessionState
from app.config_loader import load_business
from app.metrics import percentile, summarize
from app.service import FixedClock

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_business(ROOT / "config" / "business.yaml")
ZONE = ZoneInfo("America/Chicago")
WEDNESDAY = datetime(2026, 10, 21, 10, 0, tzinfo=ZONE)

DRAIN = [
    "My kitchen drain is clogged and backing up into the sink.",
    "Jordan Hale",
    "(512) 555-0164",
    "880 West Mary Street, Austin 78704",
]
CONTACT_HEATER = [
    "We have no hot water. I think the water heater is dead.",
    "Chris Patel",
    "512-555-0108",
    "18 Rio Grande Street, Austin 78701",
]


SCENARIOS = [
    {
        "id": "emergency-burst-pipe-full",
        "turns": [
            "My pipe burst at 1402 Manor Road, Austin 78702 and water is everywhere. I'm Lena Ortiz, 512-555-0177.",
        ],
        "outcome": "escalated",
        "intent": "emergency",
        "say_contains": ["emergency", "connecting you to Miguel"],
        "events": ["transfer", "lead", "webhook"],
        "events_absent": ["booking"],
    },
    {
        "id": "emergency-gas-smell",
        "turns": ["I smell gas in the laundry room."],
        "outcome": "escalated",
        "intent": "emergency",
        "say_contains": ["emergency", "Miguel", "on-call"],
        "events": ["transfer"],
    },
    {
        "id": "emergency-carbon-monoxide",
        "turns": ["The carbon monoxide detector is going off."],
        "outcome": "escalated",
        "intent": "emergency",
        "say_contains": ["emergency", "Miguel"],
        "events": ["transfer"],
    },
    {
        "id": "emergency-sewer-backup",
        "turns": ["We have a sewer backup in the downstairs bathroom at 22 Elm Street, Austin 78702."],
        "outcome": "escalated",
        "say_contains": ["emergency"],
        "events": ["transfer"],
    },
    {
        "id": "emergency-flooding",
        "turns": ["The basement flooded and there is water everywhere."],
        "outcome": "escalated",
        "intent": "emergency",
        "events": ["transfer"],
        "say_contains": ["on-call"],
    },
    {
        "id": "emergency-sparking-outlet",
        "turns": ["The outlet in the kitchen is sparking and I smell something burning."],
        "outcome": "escalated",
        "events": ["transfer"],
        "say_contains": ["emergency"],
    },
    {
        "id": "emergency-no-heat-with-baby",
        "turns": ["Our furnace is out and we have no heat with a baby in the house."],
        "outcome": "escalated",
        "intent": "emergency",
        "say_contains": ["emergency", "Miguel"],
        "events": ["transfer"],
    },
    {
        "id": "emergency-beats-quote",
        "turns": ["How much to fix a burst pipe at 500 Congress Avenue, Austin 78701?"],
        "outcome": "escalated",
        "intent": "emergency",
        "say_contains": ["emergency"],
        "transcript_absent": ["typically run"],
        "events": ["transfer"],
        "events_absent": ["booking"],
    },
    {
        "id": "spam-seo",
        "turns": ["Hi, we help plumbers rank on Google and improve their SEO listings."],
        "outcome": "spam",
        "intent": "spam",
        "say_contains": ["not able to take sales calls"],
        "events_absent": ["booking", "transfer", "lead"],
    },
    {
        "id": "spam-car-warranty",
        "turns": ["This is about your car's extended warranty."],
        "outcome": "spam",
        "intent": "spam",
        "say_contains": ["sales calls"],
    },
    {
        "id": "spam-google-listing",
        "turns": ["We can fix your Google business listing and reviews."],
        "outcome": "spam",
        "intent": "spam",
    },
    {
        "id": "spam-medicare",
        "turns": ["I'm calling about a medicare plan for your household."],
        "outcome": "spam",
        "intent": "spam",
    },
    {
        "id": "spam-marketing",
        "turns": ["We offer marketing services for plumbers."],
        "outcome": "spam",
        "intent": "spam",
        "events_absent": ["booking"],
    },
    {
        "id": "not-spam-found-on-google",
        "turns": ["I found you on Google and I have a leaking faucet."],
        "outcome": None,
        "intent": "new_job",
        "say_contains": ["Who am I speaking with"],
        "transcript_absent": ["sales calls"],
    },
    {
        "id": "book-drain-earliest",
        "turns": DRAIN + ["the earliest you have", "yes"],
        "outcome": "booked",
        "intent": "new_job",
        "say_contains": ["You're booked", "11:30 AM", "have not sent a text", "(512) 555-0164", "$89"],
        "transcript_contains": ["Who am I speaking with", "best phone number", "street address"],
        "events": ["booking", "sms", "webhook", "lead"],
        "booking_start_contains": "T11:30:00",
        "checkpoints": [{"after": 0, "contains": ["Who am I speaking with"], "outcome": None}],
    },
    {
        "id": "book-water-heater-second-slot",
        "turns": CONTACT_HEATER + ["the second one", "yes"],
        "outcome": "booked",
        "say_contains": ["You're booked", "1:00 PM"],
        "booking_start_contains": "T13:00:00",
        "events": ["booking", "sms"],
    },
    {
        "id": "book-toilet-third-slot",
        "turns": [
            "My toilet won't stop running.",
            "Alex Kim",
            "512-555-0155",
            "75 East Avenue, Austin 78702",
            "the third one",
            "yes",
        ],
        "outcome": "booked",
        "say_contains": ["You're booked", "2:30 PM"],
        "booking_start_contains": "T14:30:00",
    },
    {
        "id": "book-disposal",
        "turns": [
            "The garbage disposal is jammed.",
            "Nina Cole",
            "512.555.0114",
            "410 Brazos Street, Austin 78701",
            "the earliest you have",
            "yes",
        ],
        "outcome": "booked",
        "intent": "new_job",
        "say_contains": ["You're booked", "11:30 AM"],
        "events": ["sms"],
    },
    {
        "id": "book-faucet-tomorrow-morning",
        "turns": [
            "My bathroom faucet is leaking.",
            "Elena Brooks",
            "512-555-0148",
            "75 East Avenue, Austin 78702",
            "tomorrow morning",
            "the earliest you have",
            "yes",
        ],
        "outcome": "booked",
        "say_contains": ["You're booked", "Thursday", "7:00 AM"],
        "checkpoints": [{"after": 4, "contains": ["Thursday", "7:00 AM"]}],
        "booking_start_contains": "T07:00:00",
    },
    {
        "id": "quote-ac-then-book",
        "turns": [
            "How much to fix an AC that is not cooling?",
            "yes please",
            "Priya Raman",
            "512-555-0188",
            "410 Brazos Street, Austin 78701",
            "the earliest you have",
            "yes",
        ],
        "outcome": "booked",
        "intent": "quote",
        "transcript_contains": ["typically run", "$189", "diagnostic"],
        "say_contains": ["You're booked"],
        "events": ["booking", "webhook"],
        "checkpoints": [{"after": 0, "contains": ["typically run", "diagnostic"], "outcome": None}],
    },
    {
        "id": "quote-water-heater-decline",
        "turns": ["How much does a water heater replacement cost?", "no thanks"],
        "outcome": "missed",
        "intent": "quote",
        "transcript_contains": ["typically run", "$180"],
        "say_contains": ["ask for Riley"],
        "events_absent": ["booking", "lead"],
    },
    {
        "id": "quote-with-contact-declines-to-lead",
        "turns": [
            "How much for a drain cleaning? I'm Morgan Lee, 512-555-0194, 9 Barton Springs Road, Austin 78704.",
            "No thanks",
        ],
        "outcome": "qualified",
        "intent": "quote",
        "say_contains": ["saved your details"],
        "transcript_contains": ["typically run"],
        "events": ["lead", "webhook"],
        "events_absent": ["booking"],
    },
    {
        "id": "no-heat-books-not-escalate",
        "turns": [
            "The furnace stopped working overnight.",
            "Sam Ortiz",
            "512-555-0122",
            "15 Oak Drive, Austin 78745",
            "the earliest you have",
            "yes",
        ],
        "outcome": "booked",
        "intent": "new_job",
        "transcript_absent": ["treating this as an emergency"],
        "events": ["booking"],
        "events_absent": ["transfer"],
    },
    {
        "id": "one-utterance-then-confirm",
        "turns": [
            "I'm Jordan Hale, 5125550164, at 880 West Mary Street, Austin 78704. The kitchen drain is clogged. Book the earliest you have.",
            "yes",
        ],
        "outcome": "booked",
        "say_contains": ["You're booked", "11:30 AM", "880 West Mary Street"],
        "checkpoints": [{"after": 0, "contains": ["lock that in", "11:30 AM"], "outcome": None}],
        "events": ["sms", "booking"],
    },
    {
        "id": "abandon-missed",
        "turns": ["There is a leak under the kitchen sink.", "never mind, I gotta go"],
        "outcome": "missed",
        "say_contains": ["when you're ready"],
        "events_absent": ["booking", "transfer"],
    },
    {
        "id": "unclear-then-toilet-book",
        "turns": [
            "Hello?",
            "My toilet won't stop running.",
            "Alex Kim",
            "512-555-0155",
            "75 East Avenue, Austin 78702",
            "the earliest you have",
            "yes",
        ],
        "outcome": "booked",
        "checkpoints": [
            {"after": 0, "contains": ["new repair"], "outcome": None},
            {"after": 1, "contains": ["Who am I speaking with"]},
        ],
        "say_contains": ["You're booked", "11:30 AM"],
    },
    {
        "id": "out-of-area-los-angeles",
        "turns": [
            "This is Sam Rivera, 213-555-0199, 900 Sunset Boulevard, Los Angeles 90210. My sink is clogged.",
        ],
        "outcome": "out_of_area",
        "say_contains": ["outside our service area", "Austin"],
        "events": ["lead", "webhook"],
        "events_absent": ["booking", "transfer"],
    },
    {
        "id": "ask-zip-then-book",
        "turns": [
            "I have a leaking faucet.",
            "Sam Ortiz",
            "512-555-0122",
            "15 Oak Drive",
            "78745",
            "the earliest you have",
            "yes",
        ],
        "outcome": "booked",
        "say_contains": ["You're booked", "78745", "Oak Drive"],
        "checkpoints": [{"after": 3, "contains": ["ZIP code"], "outcome": None}],
    },
    {
        "id": "existing-reschedule-earliest",
        "preload": "dana",
        "turns": [
            "Hi this is Dana Cho, I need to reschedule my appointment to the earliest you have.",
            "0133 Thursday",
            "yes",
        ],
        "outcome": "rescheduled",
        "intent": "existing_booking",
        "say_contains": ["moved", "11:30 AM"],
        "events": ["booking", "sms", "webhook"],
        "active_start_contains": "T11:30:00",
        "checkpoints": [{"after": 1, "contains": ["currently set", "Thursday", "lock that in"]}],
    },
    {
        "id": "existing-cancel",
        "preload": "dana",
        "turns": ["This is Dana Cho. Please cancel my appointment.", "0133 Thursday", "yes"],
        "outcome": "cancelled",
        "say_contains": ["I've cancelled", "Thursday", "8:30 AM"],
        "events": ["booking", "webhook"],
        "active_booking": False,
    },
    {
        "id": "existing-unknown-name",
        "preload": "dana",
        "turns": ["I need to reschedule my appointment.", "0199 Thursday"],
        "outcome": None,
        "say_contains": ["don't have a visit"],
        "checkpoints": [{"after": 0, "contains": ["last four"]}],
        "events_absent": ["booking"],
    },
    {
        "id": "negation-no-gas-smell-books",
        "turns": [
            "There is no gas smell, just a slow drain in the kitchen.",
            "Riley Chen",
            "512-555-0160",
            "880 West Mary Street, Austin 78704",
            "the earliest you have",
            "yes",
        ],
        "outcome": "booked",
        "intent": "new_job",
        "transcript_absent": ["treating this as an emergency"],
        "events_absent": ["transfer"],
        "events": ["booking"],
    },
    {
        "id": "caller-requests-human",
        "turns": ["Can I talk to a real person?"],
        "outcome": "escalated",
        "intent": "handoff",
        "say_contains": ["asked for a person", "Miguel"],
        "events": ["transfer", "webhook"],
        "transcript_absent": ["treating this as an emergency"],
    },
    {
        "id": "after-hours-books-next-morning",
        "now": "2026-10-21T21:00:00-05:00",
        "turns": DRAIN + ["the earliest you have", "yes"],
        "outcome": "booked",
        "say_contains": ["You're booked", "Thursday", "7:00 AM"],
        "booking_start_contains": "T07:00:00",
    },
    {
        "id": "sunday-rolls-to-monday",
        "now": "2026-10-25T10:00:00-05:00",
        "turns": DRAIN + ["the earliest you have", "yes"],
        "outcome": "booked",
        "say_contains": ["Monday", "7:00 AM"],
        "booking_start_contains": "T07:00:00",
    },
    {
        "id": "saturday-hours",
        "now": "2026-10-24T09:00:00-05:00",
        "turns": DRAIN + ["the earliest you have", "yes"],
        "outcome": "booked",
        "say_contains": ["Saturday", "11:00 AM"],
        "booking_start_contains": "T11:00:00",
    },
    {
        "id": "reject-then-pick-other-slot",
        "turns": DRAIN + ["the earliest you have", "no, the second one", "yes"],
        "outcome": "booked",
        "say_contains": ["You're booked", "1:00 PM"],
        "booking_start_contains": "T13:00:00",
        "checkpoints": [
            {"after": 4, "contains": ["11:30 AM", "lock that in"]},
            {"after": 5, "contains": ["1:00 PM", "lock that in"]},
        ],
    },
]


def _run(scenario: dict):
    now = datetime.fromisoformat(scenario["now"]) if scenario.get("now") else WEDNESDAY
    clock = FixedClock(now)
    calendar = MemoryCalendar()
    if scenario.get("preload") == "dana":
        start = datetime(2026, 10, 22, 8, 30, tzinfo=ZONE)
        calendar.book(
            {
                "id": "bk_dana",
                "name": "Dana Cho",
                "phone": "5125550133",
                "address": "22 Elm Street, Austin 78702",
                "issue": "Annual water heater flush",
                "start": start.isoformat(),
                "end": (start + timedelta(minutes=90)).isoformat(),
            }
        )
    engine = Engine(CONFIG, calendar, clock)
    state = SessionState()
    greeting = engine.greeting(state)
    assert "porter plumbing" in greeting.say.lower()
    assert "riley" in greeting.say.lower()
    assert "virtual receptionist" in greeting.say.lower()
    says = [greeting.say]
    events: list[dict] = []
    latencies = [greeting.latency_ms]
    last = greeting
    for index, line in enumerate(scenario["turns"]):
        last = engine.handle(state, line)
        says.append(last.say)
        events.extend(last.events)
        latencies.append(last.latency_ms)
        assert last.latency_ms < 250, (scenario["id"], last.latency_ms, line)
        for check in scenario.get("checkpoints", []):
            if check["after"] != index:
                continue
            for bit in check.get("contains", []):
                assert bit.lower() in last.say.lower(), (scenario["id"], bit, last.say)
            if "outcome" in check:
                assert state.outcome == check["outcome"], (scenario["id"], state.outcome)
    transcript = "\n".join(says).lower()
    if "outcome" in scenario:
        assert state.outcome == scenario["outcome"], (scenario["id"], state.outcome, last.say)
    if "intent" in scenario:
        assert state.intent == scenario["intent"], (scenario["id"], state.intent, last.say)
    for bit in scenario.get("say_contains", []):
        assert bit.lower() in last.say.lower(), (scenario["id"], bit, last.say)
    for bit in scenario.get("transcript_contains", []):
        assert bit.lower() in transcript, (scenario["id"], bit, last.say)
    for bit in scenario.get("transcript_absent", []):
        assert bit.lower() not in transcript, (scenario["id"], bit, transcript)
    kinds = [event["type"] for event in events]
    for kind in scenario.get("events", []):
        assert kind in kinds, (scenario["id"], kind, kinds)
    for kind in scenario.get("events_absent", []):
        assert kind not in kinds, (scenario["id"], kind, kinds)
    if scenario.get("booking_start_contains"):
        bookings = [event for event in events if event["type"] == "booking"]
        assert bookings, scenario["id"]
        assert scenario["booking_start_contains"] in bookings[-1]["payload"]["start"], bookings[-1]
    if scenario.get("active_booking") is False:
        assert calendar.find(state.name, state.phone) is None
    if scenario.get("active_start_contains"):
        found = calendar.find("Dana Cho", None)
        assert found is not None
        assert scenario["active_start_contains"] in found["start"]
    return latencies


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[item["id"] for item in SCENARIOS])
def test_caller_scenario(scenario):
    _run(scenario)


def test_catalog_has_at_least_30_scenarios():
    assert len(SCENARIOS) >= 30


def test_latency_metrics_across_scenarios():
    samples: list[float] = []
    for scenario in SCENARIOS:
        samples.extend(_run(scenario))
    report = summarize(samples)
    assert report["count"] == len(samples)
    assert report["count"] > 100
    assert report["p50_ms"] is not None
    assert report["p95_ms"] < 250
    assert report["max_ms"] < 250
    assert percentile([10, 20, 30, 40, 100], 0.5) == 30
    assert summarize([])["count"] == 0


def test_two_callers_do_not_share_a_slot():
    clock = FixedClock(WEDNESDAY)
    calendar = MemoryCalendar()
    engine = Engine(CONFIG, calendar, clock)
    first = SessionState()
    engine.greeting(first)
    for line in DRAIN + ["the earliest you have", "yes"]:
        engine.handle(first, line)
    assert first.outcome == "booked"
    second = SessionState()
    engine.greeting(second)
    last = None
    for line in [
        "The garbage disposal is jammed.",
        "Nina Cole",
        "512-555-0114",
        "410 Brazos Street, Austin 78701",
        "the earliest you have",
        "yes",
    ]:
        last = engine.handle(second, line)
    assert second.outcome == "booked"
    assert last is not None
    assert "1:00 PM" in last.say
    assert "11:30 AM" not in last.say
