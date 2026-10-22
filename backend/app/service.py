"""Wire the engine to storage, CRM delivery, and the optional Claude dialog."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from time import perf_counter
from uuid import uuid4

from app.agent.dialog import Dialog
from app.agent.engine import Engine, SessionState
from app.agent.nlu import caller_id_digits
from app.agent.scheduling import available_slots, format_slot
from app.config_loader import BusinessConfig
from app.integrations import deliver_webhook, enqueue_webhook
from app.llm.claude import ClaudeClient
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
        model = settings.model_client
        if model is None and settings.anthropic_api_key:
            model = ClaudeClient(settings.anthropic_api_key, settings.anthropic_model)
        self.dialog = Dialog(self.engine, model)
        self._guard = threading.Lock()
        self._call_locks: dict[str, threading.Lock] = {}

    def _lock_for(self, call_id: str) -> threading.Lock:
        with self._guard:
            lock = self._call_locks.get(call_id)
            if lock is None:
                lock = threading.Lock()
                self._call_locks[call_id] = lock
            return lock

    def start(self, channel: str, external_id: str | None = None, caller_id: str | None = None) -> dict:
        call_id = "call_" + uuid4().hex[:12]
        state = SessionState(call_id=call_id, caller_id=caller_id_digits(caller_id))
        result = self.engine.greeting(state)
        now = self.clock.now()
        self.store.create_call(call_id, channel, external_id, now, state)
        self.store.add_turn(call_id, "agent", result.say, result.latency_ms, now)
        self.store.save_state(call_id, state, ended=False, ended_at=None)
        return self._public(call_id, result.say, result, state)

    def turn(self, call_id: str, text: str, caller_id: str | None = None) -> dict:
        text = (text or "")[:2000]
        wall = perf_counter()
        with self._lock_for(call_id):
            state = self.store.load_state(call_id)
            if caller_id and not state.caller_id:
                state.caller_id = caller_id_digits(caller_id)
            if text and state.last_caller_text == text and state.last_reply:
                cached = self._public(call_id, state.last_reply, type("R", (), {"latency_ms": 0.0, "events": []})(), state)
                cached["duplicate"] = True
                cached["engine_ms"] = 0.0
                return cached
            now = self.clock.now()
            self.store.add_turn(call_id, "caller", text, None, now)
            result = self.dialog.handle(state, text)
            state.last_caller_text = text
            engine_ms = result.latency_ms
            result.latency_ms = (perf_counter() - wall) * 1000
            self.store.add_turn(call_id, "agent", result.say, result.latency_ms, now)
            self._apply(call_id, result, now)
            ended = state.outcome is not None
            self.store.save_state(call_id, state, ended=ended, ended_at=now if ended else None)
            public = self._public(call_id, result.say, result, state)
            public["engine_ms"] = round(engine_ms, 2)
            return public

    def reset_and_seed(self, seed_fn) -> dict:
        self.store.wipe()
        seed_fn(self)
        return {"ok": True, "calls": self.store.count_calls()}

    def _apply(self, call_id: str, result, now: datetime) -> None:
        for event in result.events:
            payload = dict(event["payload"])
            status = None
            if event["type"] == "webhook":
                secret = self.settings.webhook_secret
                if self.config.webhook_url:
                    delivery = enqueue_webhook(self.config.webhook_url, payload, secret, lambda _result: None)
                else:
                    delivery = deliver_webhook("", payload, secret)
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
            "language": state.language,
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
