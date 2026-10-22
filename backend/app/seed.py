"""Pre-baked calls for the first launch.

Times and durations are written in, not produced by replaying dialogs at startup.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from app.agent.engine import SessionState, summarize

logger = logging.getLogger(__name__)


def seed_demo(service) -> list[dict]:
    """Insert the sample day. This does not run the dialog, so it does not need the hazard models."""
    try:
        planted = _plant_day(service)
    except Exception:
        logger.warning("Could not plant the sample day", exc_info=True)
        return []
    try:
        service.plant_existing_booking()
    except Exception:
        logger.warning("Could not plant the sample booking", exc_info=True)
    return planted


def _at(moment: datetime, day: int, hour: int, minute: int) -> datetime:
    base = moment.astimezone(moment.tzinfo).replace(hour=0, minute=0, second=0, microsecond=0)
    return base + timedelta(days=day, hours=hour, minutes=minute)


def _plant_day(service) -> list[dict]:
    moment = service.clock.now()
    rows = [
        {
            "id": "call_seed_lena",
            "channel": "phone",
            "start": _at(moment, 0, 8, 12),
            "minutes": 3,
            "seconds": 40,
            "name": "Lena Ortiz",
            "phone": "5125550177",
            "address": "1402 Manor Road, Austin 78702",
            "issue": "Burst pipe",
            "intent": "emergency",
            "outcome": "escalated",
            "caller": "My pipe burst and water is everywhere. I'm Lena Ortiz.",
            "reply": "I'm connecting you to Miguel Santos, our on-call technician.",
        },
        {
            "id": "call_seed_spam",
            "channel": "phone",
            "start": _at(moment, 0, 9, 5),
            "minutes": 2,
            "seconds": 12,
            "name": None,
            "phone": None,
            "address": None,
            "issue": "SEO pitch",
            "intent": "spam",
            "outcome": "spam",
            "caller": "Hi, we help plumbers rank on Google and improve their SEO listings.",
            "reply": "I appreciate you thinking of us, but we're not able to take sales calls.",
        },
        {
            "id": "call_seed_jordan",
            "channel": "simulator",
            "start": _at(moment, 0, 10, 18),
            "minutes": 5,
            "seconds": 5,
            "name": "Jordan Hale",
            "phone": "5125550164",
            "address": "880 West Mary Street, Austin 78704",
            "issue": "Clogged drain",
            "intent": "new_job",
            "outcome": "booked",
            "caller": "My kitchen drain is clogged and backing up into the sink.",
            "reply": "You're booked. The technician will see you this afternoon.",
            "booking": {"day": 0, "hour": 16, "minute": 0},
        },
        {
            "id": "call_seed_priya",
            "channel": "phone",
            "start": _at(moment, 0, 11, 40),
            "minutes": 5,
            "seconds": 18,
            "name": "Priya Raman",
            "phone": "5125550188",
            "address": "410 Brazos Street, Austin 78701",
            "issue": "AC repair",
            "intent": "new_job",
            "outcome": "booked",
            "caller": "The AC is not cooling.",
            "reply": "You're booked for tomorrow afternoon.",
            "booking": {"day": 1, "hour": 13, "minute": 0},
        },
        {
            "id": "call_seed_quote",
            "channel": "phone",
            "start": _at(moment, 0, 13, 6),
            "minutes": 2,
            "seconds": 40,
            "name": None,
            "phone": None,
            "address": None,
            "issue": "Water heater",
            "intent": "quote",
            "outcome": "missed",
            "caller": "How much does a water heater replacement cost?",
            "reply": "No problem. We'll be here when you're ready.",
        },
        {
            "id": "call_seed_leak",
            "channel": "phone",
            "start": _at(moment, 0, 14, 22),
            "minutes": 3,
            "seconds": 11,
            "name": None,
            "phone": None,
            "address": None,
            "issue": "Leak",
            "intent": "new_job",
            "outcome": "missed",
            "caller": "There is a leak under the kitchen sink.",
            "reply": "No problem. We'll be here when you're ready.",
        },
        {
            "id": "call_seed_chris",
            "channel": "phone",
            "start": _at(moment, 0, 15, 48),
            "minutes": 5,
            "seconds": 48,
            "name": "Chris Patel",
            "phone": "5125550108",
            "address": "18 Rio Grande Street, Austin 78701",
            "issue": "Water heater",
            "intent": "new_job",
            "outcome": "booked",
            "caller": "We have no hot water. I think the water heater is dead.",
            "reply": "You're booked for tomorrow morning.",
            "booking": {"day": 1, "hour": 9, "minute": 0},
        },
    ]
    planted = []
    for row in rows:
        end = row["start"] + timedelta(minutes=row["minutes"], seconds=row["seconds"])
        state = SessionState(
            phase="closed",
            intent=row["intent"],
            name=row["name"],
            phone=row["phone"],
            address=row["address"],
            issue=row["issue"],
            outcome=row["outcome"],
            call_id=row["id"],
            hazard="Burst pipe" if row["outcome"] == "escalated" else None,
        )
        service.store.create_call(row["id"], row["channel"], None, row["start"], state)
        service.store.add_turn(row["id"], "agent", "Thank you for calling Northline Plumbing. What's going on?", 3.2, row["start"])
        service.store.add_turn(row["id"], "caller", row["caller"], None, row["start"] + timedelta(seconds=20))
        service.store.add_turn(row["id"], "agent", row["reply"], 6.4, end)
        service.store.save_state(row["id"], state, ended=True, ended_at=end)
        booking = row.get("booking")
        if booking:
            start = _at(moment, booking["day"], booking["hour"], booking["minute"])
            service.engine.calendar.book(
                {
                    "id": "bk_" + row["id"],
                    "call_id": row["id"],
                    "name": row["name"],
                    "phone": row["phone"],
                    "address": row["address"],
                    "issue": row["issue"],
                    "start": start.isoformat(),
                    "end": (start + timedelta(minutes=service.config.slot_minutes)).isoformat(),
                }
            )
        planted.append({"id": row["id"], "outcome": row["outcome"], "summary": summarize(state)})
    return planted
