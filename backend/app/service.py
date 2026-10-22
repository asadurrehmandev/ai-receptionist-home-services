"""Wire the engine to storage, CRM delivery, and optional LLM phrasing."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from app.agent.engine import Engine, SessionState
from app.agent.scheduling import available_slots, format_slot
from app.config_loader import BusinessConfig
from app.integrations import deliver_webhook, rephrase
from app.store import Store, StoreCalendar


class SystemClock:
    def __init__(self, zone) -> None:
        self.zone = zone

    def now(self) -> datetime:
        return datetime.now(self.zone)


class FixedClock:
    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def now(self) -> datetime:
        return self.moment


class ReceptionService:
    def __init__(self, config: BusinessConfig, store: Store, settings, clock=None) -> None:
        self.config = config
        self.store = store
        self.settings = settings
        self.clock = clock or SystemClock(config.zone)
        self.engine = Engine(config, StoreCalendar(store), self.clock)

    def start(self, channel: str, external_id: str | None = None) -> dict:
        call_id = "call_" + uuid4().hex[:12]
        state = SessionState(call_id=call_id)
        result = self.engine.greeting(state)
        now = self.clock.now()
        self.store.create_call(call_id, channel, external_id, now, state)
        self.store.add_turn(call_id, "agent", result.say, result.latency_ms, now)
        self.store.save_state(call_id, state, ended=False, ended_at=None)
        return self._public(call_id, result.say, result, state)

    def turn(self, call_id: str, text: str) -> dict:
        state = self.store.load_state(call_id)
        now = self.clock.now()
        self.store.add_turn(call_id, "caller", text, None, now)
        result = self.engine.handle(state, text)
        spoken = rephrase(result.say, state, text, self.settings)
        result.say = spoken
        self.store.add_turn(call_id, "agent", spoken, result.latency_ms, now)
        self._apply(call_id, result, now)
        ended = state.outcome is not None
        self.store.save_state(call_id, state, ended=ended, ended_at=now if ended else None)
        return self._public(call_id, spoken, result, state)

    def reset_and_seed(self, seed_fn) -> dict:
        self.store.wipe()
        seed_fn(self)
        return {"ok": True, "calls": self.store.count_calls()}

    def _apply(self, call_id: str, result, now: datetime) -> None:
        for event in result.events:
            payload = dict(event["payload"])
            status = None
            if event["type"] == "webhook":
                delivery = deliver_webhook(self.config.webhook_url, payload)
                payload["delivery"] = delivery
                status = delivery["status"]
            elif event["type"] == "sms":
                status = "logged"
            elif event["type"] == "transfer":
                status = "transfer"
            self.store.add_event(call_id, event["type"], payload, status, now)
            if event["type"] == "lead":
                self.store.upsert_lead(payload, now)

    def _public(self, call_id: str, say: str, result, state: SessionState) -> dict:
        offered = []
        for value in state.offered:
            offered.append(format_slot(datetime.fromisoformat(value)))
        return {
            "id": call_id,
            "say": say,
            "outcome": state.outcome,
            "intent": state.intent,
            "phase": state.phase,
            "latency_ms": round(result.latency_ms, 2),
            "slots": {
                "name": state.name,
                "phone": state.phone,
                "address": state.address,
                "issue": state.issue,
                "zip": state.zip,
                "city": state.city,
            },
            "offered": offered,
            "events": result.events,
        }

    def plant_existing_booking(self) -> dict | None:
        """Hold a named visit so the reschedule demo has someone to move."""
        slots, _ = available_slots(self.config, self.clock.now(), self.engine.calendar.busy(), limit=6)
        mornings = [slot for slot in slots if slot.hour < 12]
        choice = mornings[0] if mornings else (slots[0] if slots else None)
        if choice is None:
            return None
        end = choice + timedelta(minutes=self.config.slot_minutes)
        return self.engine.calendar.book(
            {
                "id": "bk_dana_cho",
                "call_id": None,
                "name": "Dana Cho",
                "phone": "5125550133",
                "address": "22 Elm Street, Austin 78702",
                "issue": "Annual water heater flush",
                "start": choice.isoformat(),
                "end": end.isoformat(),
            }
        )
