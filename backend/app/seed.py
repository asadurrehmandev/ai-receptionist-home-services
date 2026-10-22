"""Replay realistic calls so the dashboard is not empty on first launch."""

from __future__ import annotations

SEED_SCRIPTS: list[dict] = [
    {
        "id": "burst-lena",
        "channel": "phone",
        "turns": [
            "My pipe burst at 1402 Manor Road, Austin 78702 and water is everywhere. I'm Lena Ortiz, 512-555-0177.",
        ],
        "outcome": "escalated",
    },
    {
        "id": "spam-seo",
        "channel": "phone",
        "turns": ["Hi, we help plumbers rank on Google and improve their SEO listings."],
        "outcome": "spam",
    },
    {
        "id": "drain-jordan",
        "channel": "simulator",
        "turns": [
            "My kitchen drain is clogged and backing up into the sink.",
            "Jordan Hale",
            "512-555-0164",
            "880 West Mary Street, Austin 78704",
            "the earliest you have",
            "yes",
        ],
        "outcome": "booked",
    },
    {
        "id": "ac-priya",
        "channel": "phone",
        "turns": [
            "The AC is not cooling.",
            "Priya Raman",
            "512-555-0188",
            "410 Brazos Street, Austin 78701",
            "tomorrow afternoon",
            "the earliest you have",
            "yes",
        ],
        "outcome": "booked",
    },
    {
        "id": "quote-decline",
        "channel": "phone",
        "turns": [
            "How much does a water heater replacement cost?",
            "no thanks",
        ],
        "outcome": "missed",
    },
    {
        "id": "leak-abandon",
        "channel": "phone",
        "turns": [
            "There is a leak under the kitchen sink.",
            "never mind, I gotta go",
        ],
        "outcome": "missed",
    },
    {
        "id": "heater-second",
        "channel": "phone",
        "turns": [
            "We have no hot water. I think the water heater is dead.",
            "Chris Patel",
            "512-555-0108",
            "18 Rio Grande Street, Austin 78701",
            "the second one",
            "yes",
        ],
        "outcome": "booked",
    },
]


def seed_demo(service) -> list[dict]:
    results = []
    for script in SEED_SCRIPTS:
        call = service.start(script["channel"])
        last = call
        for line in script["turns"]:
            last = service.turn(call["id"], line)
        if last["outcome"] != script["outcome"]:
            raise RuntimeError(
                f"Seed script {script['id']} ended as {last['outcome']!r}, expected {script['outcome']!r}. Last reply: {last['say']}"
            )
        results.append(last)
    service.plant_existing_booking()
    return results
