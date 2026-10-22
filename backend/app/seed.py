"""Replay realistic calls so the dashboard is not empty on first launch."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

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
    """Seed the board. A missing hazard model must not stop the process."""
    from app.agent.hazard_nli import nli_ready
    from app.agent.hazard_semantic import semantic_ready

    from app.agent.understand import pause_understand, understand_enabled, understand_ready

    if not semantic_ready() or not nli_ready():
        logger.warning("A safety model is not loaded. Skipping demo seed.")
        return []
    if understand_enabled() and not understand_ready():
        logger.warning("The understander is not available. Skipping demo seed.")
        return []
    with pause_understand():
        return _seed_scripts(service)


def _seed_scripts(service) -> list[dict]:
    results = []
    for script in SEED_SCRIPTS:
        try:
            call = service.start(script["channel"])
            last = call
            for line in script["turns"]:
                last = service.turn(call["id"], line)
            if last["outcome"] != script["outcome"]:
                logger.warning(
                    "Seed script %s ended as %r, expected %r. Last reply: %s",
                    script["id"],
                    last["outcome"],
                    script["outcome"],
                    last["say"],
                )
                continue
            results.append(last)
        except Exception:
            logger.warning("Seed script %s failed", script["id"], exc_info=True)
    try:
        service.plant_existing_booking()
    except Exception:
        logger.warning("Could not plant the sample booking", exc_info=True)
    return results
