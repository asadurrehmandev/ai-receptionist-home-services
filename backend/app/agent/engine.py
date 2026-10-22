"""Rule-based receptionist. Safe to run with no paid API keys."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from time import perf_counter
from uuid import uuid4

from app.agent.calendar import Calendar, new_booking_id
from app.agent.nlu import (
    detect_emergency,
    detect_intent,
    extract_city,
    extract_introduced_name,
    extract_issue,
    extract_phone,
    extract_street,
    extract_zip,
    format_phone,
    guess_bare_name,
    is_no,
    is_spam,
    is_yes,
    wants_abandon,
    wants_cancel,
    wants_human,
    wants_reschedule,
)
from app.agent.scheduling import available_slots, format_slot, join_slots, match_offered, parse_preference
from app.config_loader import BusinessConfig


@dataclass
class SessionState:
    phase: str = "discover"
    intent: str | None = None
    name: str | None = None
    phone: str | None = None
    street: str | None = None
    address: str | None = None
    zip: str | None = None
    city: str | None = None
    issue: str | None = None
    outcome: str | None = None
    offered: list[str] = field(default_factory=list)
    selected: str | None = None
    quote_given: bool = False
    booking_id: str | None = None
    pending_action: str | None = None
    call_id: str | None = None
    events: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> SessionState:
        known = {item.name for item in cls.__dataclass_fields__.values()}
        return cls(**{key: value for key, value in raw.items() if key in known})


@dataclass
class TurnResult:
    say: str
    events: list[dict]
    latency_ms: float


class Engine:
    def __init__(self, config: BusinessConfig, calendar: Calendar, clock) -> None:
        self.config = config
        self.calendar = calendar
        self.clock = clock

    @property
    def now(self) -> datetime:
        return self.clock.now()

    def greeting(self, state: SessionState) -> TurnResult:
        started = perf_counter()
        state.phase = "discover"
        say = (
            f"Thank you for calling {self.config.name}. I'm {self.config.agent_name}, the virtual receptionist. "
            "I can book a technician, give a ballpark price, or connect you to on-call if this is an emergency. "
            "What's going on?"
        )
        return self._finish(state, say, started)

    def handle(self, state: SessionState, text: str) -> TurnResult:
        started = perf_counter()
        raw = (text or "").strip()
        if not raw:
            return self._finish(state, "I didn't catch that. What's going on at the property?", started)
        if state.phase == "closed":
            return self._finish(
                state,
                "This call has ended. Please call back if something else comes up.",
                started,
            )

        emergency = detect_emergency(raw)
        if emergency:
            self._fill(state, raw)
            state.intent = "emergency"
            state.issue = emergency
            return self._escalate(state, started, emergency)

        if wants_human(raw):
            self._fill(state, raw)
            state.intent = state.intent or "handoff"
            return self._escalate(state, started, "Caller requested a person")

        if wants_abandon(raw):
            state.outcome = "missed"
            state.phase = "closed"
            return self._finish(state, "No problem. We'll be here when you're ready. Goodbye.", started)

        if state.phase == "discover" and is_spam(raw):
            state.intent = "spam"
            state.outcome = "spam"
            state.phase = "closed"
            return self._finish(
                state,
                "I appreciate you thinking of us, but we're not able to take sales calls. Have a good day.",
                started,
            )

        if state.phase == "discover":
            self._fill(state, raw)
            if state.intent in {None, "unclear"}:
                state.intent = detect_intent(raw)
            if state.intent in {None, "unclear"} and state.issue:
                state.intent = "new_job"
            if state.intent == "spam":
                state.outcome = "spam"
                state.phase = "closed"
                return self._finish(
                    state,
                    "I appreciate you thinking of us, but we're not able to take sales calls. Have a good day.",
                    started,
                )
            if state.intent == "unclear":
                return self._finish(
                    state,
                    "I can help with a new repair, an estimate, an existing appointment, or an emergency. What's going on?",
                    started,
                )
            if state.intent == "existing_booking":
                return self._existing(state, raw, started)
            return self._continue_intake(state, raw, started)

        if state.phase == "existing_lookup":
            self._fill(state, raw)
            if not state.name:
                guessed = guess_bare_name(raw)
                if guessed:
                    state.name = guessed
            if not state.name and not state.phone:
                return self._finish(state, "Sorry, I missed the name. What name is the appointment under?", started)
            return self._existing(state, raw, started)

        if state.phase == "existing_action":
            self._fill(state, raw)
            return self._existing(state, raw, started)

        if state.phase in {"collect_issue", "collect_name", "collect_phone", "collect_address", "collect_zip"}:
            self._fill(state, raw)
            if state.phase == "collect_issue" and not state.issue:
                return self._finish(state, "Tell me a bit more about what's going wrong.", started)
            if state.phase == "collect_name" and not state.name:
                return self._finish(state, "Sorry, I missed the name. Who am I speaking with?", started)
            if state.phase == "collect_phone" and not state.phone:
                return self._finish(state, "I still need a phone number. What's the best number for the technician?", started)
            if state.phase == "collect_address" and not state.street:
                return self._finish(state, "I still need the street address. What's the house number and street?", started)
            if state.phase == "collect_zip" and self._area(state) == "unknown":
                return self._finish(state, "Which ZIP code is the property in?", started)
            return self._continue_intake(state, raw, started)

        if state.phase == "quote_decision":
            self._fill(state, raw)
            if is_yes(raw):
                return self._continue_intake(state, raw, started)
            if is_no(raw):
                return self._decline_quote(state, started)
            return self._finish(state, self._quote_line(state) + " Should I book the diagnostic?", started)

        if state.phase == "offer":
            self._fill(state, raw)
            return self._on_offer(state, raw, started)

        if state.phase == "confirm":
            self._fill(state, raw)
            return self._on_confirm(state, raw, started)

        return self._finish(
            state,
            "I can help with a new repair, an estimate, an existing appointment, or an emergency. What's going on?",
            started,
        )

    def _fill(self, state: SessionState, text: str) -> None:
        phone, _ = extract_phone(text)
        if phone and not state.phone:
            state.phone = phone
        if not state.zip:
            found_zip = extract_zip(text)
            if found_zip:
                state.zip = found_zip
        if not state.city:
            city = extract_city(text, self.config.cities)
            if city:
                state.city = city
        if not state.street:
            street = extract_street(text)
            if street:
                state.street = street
        if state.street:
            state.address = _compose_address(state.street, state.city, state.zip)
        issue = extract_issue(text)
        if issue and not state.issue:
            state.issue = issue
        if not state.name:
            if state.phase == "collect_name":
                guessed = guess_bare_name(text)
                if guessed:
                    state.name = guessed
            else:
                introduced = extract_introduced_name(text)
                if introduced:
                    state.name = introduced
        if state.phase == "collect_issue" and not state.issue:
            cleaned = " ".join(text.split())
            if len(cleaned.split()) >= 3:
                state.issue = cleaned[:80].rstrip(".")

    def _continue_intake(self, state: SessionState, text: str, started: float) -> TurnResult:
        if not state.issue:
            state.phase = "collect_issue"
            return self._finish(state, "What seems to be the problem at the property?", started)
        if state.intent == "quote" and not state.quote_given:
            state.quote_given = True
            state.phase = "quote_decision"
            return self._finish(
                state,
                self._quote_line(state) + " Want me to book a diagnostic visit?",
                started,
            )
        if not state.name:
            state.phase = "collect_name"
            return self._finish(state, "Who am I speaking with?", started)
        if not state.phone:
            state.phase = "collect_phone"
            return self._finish(state, "What's the best phone number for the technician?", started)
        if not state.street:
            state.phase = "collect_address"
            return self._finish(state, "What's the street address?", started)
        if self._area(state) == "unknown":
            state.phase = "collect_zip"
            return self._finish(state, "Which ZIP code is the property in?", started)
        if self._area(state) == "no":
            return self._out_of_area(state, started)
        return self._offer(state, text, started)

    def _offer(self, state: SessionState, text: str, started: float) -> TurnResult:
        preference = parse_preference(text, self.now)
        slots, relaxed = available_slots(
            self.config,
            self.now,
            self.calendar.busy(),
            preference=preference,
            limit=3,
        )
        if not slots:
            state.phase = "closed"
            state.outcome = "qualified" if (state.phone or state.name) else "missed"
            events = self._capture_events(state, "lead.unscheduled") if state.phone or state.name else []
            return self._finish(
                state,
                "I don't have an open visit in the next two weeks. I'll have the office call you back.",
                started,
                events,
            )
        state.offered = [slot.isoformat() for slot in slots]
        choice = match_offered(slots, text)
        prefix = ""
        if relaxed and preference is not None:
            prefix = f"I don't have a {preference.label} opening. "
        if choice is not None:
            state.selected = choice.isoformat()
            state.phase = "confirm"
            return self._finish(state, prefix + self._confirm_line(state, choice), started)
        state.selected = None
        state.phase = "offer"
        return self._finish(
            state,
            f"{prefix}I can come {join_slots(slots)}. Which works best?",
            started,
        )

    def _on_offer(self, state: SessionState, text: str, started: float) -> TurnResult:
        preference = parse_preference(text, self.now)
        offered = self._offered(state)
        choice = match_offered(offered, text)
        if preference is not None and not _choice_fits(choice, preference):
            return self._offer(state, text, started)
        if choice is None:
            return self._finish(
                state,
                f"I have {join_slots(offered)}. Which of those works?",
                started,
            )
        state.selected = choice.isoformat()
        state.phase = "confirm"
        return self._finish(state, self._confirm_line(state, choice), started)

    def _on_confirm(self, state: SessionState, text: str, started: float) -> TurnResult:
        offered = self._offered(state)
        choice = match_offered(offered, text)
        if choice is not None and choice.isoformat() != state.selected:
            state.selected = choice.isoformat()
            return self._finish(state, self._confirm_line(state, choice), started)
        if is_yes(text):
            reschedule = state.intent == "existing_booking" and bool(state.booking_id)
            return self._book(state, started, reschedule=reschedule)
        if is_no(text):
            state.selected = None
            state.phase = "offer"
            return self._finish(
                state,
                f"No problem. I can come {join_slots(offered)}. Which works best?",
                started,
            )
        return self._finish(state, "Should I lock that in, or would you rather pick a different time?", started)

    def _book(self, state: SessionState, started: float, reschedule: bool) -> TurnResult:
        if not state.selected:
            return self._offer(state, "", started)
        start = datetime.fromisoformat(state.selected)
        end = start + timedelta(minutes=self.config.slot_minutes)
        if reschedule and state.booking_id:
            record = self.calendar.reschedule(state.booking_id, start, end)
            outcome = "rescheduled"
            event_name = "job.rescheduled"
            say = (
                f"You're moved to {format_slot(start)} at {state.address}. "
                f"I'll text a confirmation to {format_phone(state.phone)}."
            )
        else:
            record = self.calendar.book(
                {
                    "id": new_booking_id(),
                    "call_id": state.call_id,
                    "name": state.name,
                    "phone": state.phone,
                    "address": state.address,
                    "issue": state.issue,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                }
            )
            state.booking_id = record["id"]
            outcome = "booked"
            event_name = "job.booked"
            say = (
                f"You're booked for {format_slot(start)} at {state.address}. "
                f"I'll text a confirmation to {format_phone(state.phone)}. "
                f"The diagnostic visit is ${self.config.diagnostic_fee_usd} and we waive it if you approve the repair."
            )
        state.outcome = outcome
        state.phase = "closed"
        events = [
            {"type": "booking", "payload": record},
            {"type": "lead", "payload": _lead_payload(state, outcome)},
            {"type": "sms", "payload": {"to": state.phone, "body": self._sms(state, start, outcome)}},
            {"type": "webhook", "payload": self._webhook(state, event_name, start)},
        ]
        return self._finish(state, say, started, events)

    def _existing(self, state: SessionState, text: str, started: float) -> TurnResult:
        state.intent = "existing_booking"
        if wants_cancel(text):
            state.pending_action = "cancel"
        elif wants_reschedule(text):
            state.pending_action = "reschedule"
        if not state.name and not state.phone:
            state.phase = "existing_lookup"
            return self._finish(state, "I can pull that up. What name is the appointment under?", started)
        found = self.calendar.find(state.name, state.phone)
        if not found:
            state.intent = None
            state.phase = "discover"
            state.pending_action = None
            return self._finish(
                state,
                "I don't have an appointment under that name. If this is a new repair, tell me what's going on.",
                started,
            )
        state.booking_id = found["id"]
        state.name = state.name or found.get("name")
        state.phone = state.phone or found.get("phone")
        state.address = state.address or found.get("address")
        state.issue = state.issue or found.get("issue")
        when = format_slot(datetime.fromisoformat(found["start"]))
        if state.pending_action == "cancel":
            cancelled = self.calendar.cancel(found["id"])
            state.outcome = "cancelled"
            state.phase = "closed"
            events = [
                {"type": "booking", "payload": cancelled},
                {"type": "sms", "payload": {"to": state.phone, "body": f"{self.config.name}: your visit on {when} is cancelled."}},
                {"type": "webhook", "payload": self._webhook(state, "job.cancelled", None)},
            ]
            return self._finish(
                state,
                f"I've cancelled the visit on {when}. Call us if you need a new time.",
                started,
                events,
            )
        if state.pending_action == "reschedule":
            result = self._offer(state, text, started)
            result.say = f"You're currently set for {when}. " + result.say
            return result
        state.phase = "existing_action"
        return self._finish(
            state,
            f"I have you down for {when} at {found.get('address')}. Do you want to reschedule or cancel?",
            started,
        )

    def _escalate(self, state: SessionState, started: float, reason: str) -> TurnResult:
        state.outcome = "escalated"
        state.phase = "closed"
        who = self.config.on_call_name
        if reason == "Caller requested a person":
            say = (
                f"You asked for a person, so I'm connecting you to {who}, our on-call technician. "
                "Please stay on the line."
            )
        else:
            say = (
                f"I'm treating this as an emergency and connecting you to {who}, our on-call technician. "
                "Please stay on the line."
            )
        if state.address:
            say += f" I have the service address as {state.address}."
        events = [
            {
                "type": "transfer",
                "payload": {
                    "to_name": who,
                    "to_phone": self.config.on_call_phone,
                    "reason": reason,
                },
            },
            {"type": "lead", "payload": _lead_payload(state, "escalated")},
            {"type": "webhook", "payload": self._webhook(state, "call.escalated", None, reason=reason)},
        ]
        return self._finish(state, say, started, events)

    def _out_of_area(self, state: SessionState, started: float) -> TurnResult:
        cities = list(self.config.cities)
        if len(cities) > 1:
            served = ", ".join(cities[:-1]) + f", and {cities[-1]}"
        else:
            served = cities[0] if cities else self.config.city
        state.outcome = "out_of_area"
        state.phase = "closed"
        events = self._capture_events(state, "call.out_of_area")
        return self._finish(
            state,
            f"That address is outside our service area. We serve {served}. I can't book a truck there.",
            started,
            events,
        )

    def _decline_quote(self, state: SessionState, started: float) -> TurnResult:
        state.phase = "closed"
        if state.phone or state.name:
            state.outcome = "qualified"
            events = self._capture_events(state, "lead.qualified")
            return self._finish(
                state,
                f"Understood. I saved your details in case you want a visit later. Goodbye.",
                started,
                events,
            )
        state.outcome = "missed"
        return self._finish(
            state,
            f"Understood. If you want a visit later, call us and ask for {self.config.agent_name}. Goodbye.",
            started,
        )

    def _quote_line(self, state: SessionState) -> str:
        rule = self.config.price_for(f"{state.issue or ''}")
        fee = self.config.diagnostic_fee_usd
        if rule is None:
            return (
                f"Most visits start with a ${fee} diagnostic fee that we waive if you approve the repair."
            )
        return (
            f"For {rule.label.lower()}, jobs typically run ${rule.low_usd:,} to ${rule.high_usd:,}, "
            f"plus a ${fee} diagnostic fee that we waive if you approve the repair."
        )

    def _sms(self, state: SessionState, start: datetime, outcome: str) -> str:
        when = format_slot(start)
        if outcome == "rescheduled":
            return (
                f"{self.config.name}: your visit is moved to {when} at {state.address}. Reply STOP to opt out."
            )
        return (
            f"{self.config.name}: you're confirmed for {when} at {state.address}. "
            f"Diagnostic visit ${self.config.diagnostic_fee_usd}. Reply STOP to opt out."
        )

    def _webhook(self, state: SessionState, event: str, start: datetime | None, reason: str | None = None) -> dict:
        return {
            "event": event,
            "business": self.config.name,
            "source": "ai_receptionist",
            "call_id": state.call_id,
            "contact": {
                "name": state.name,
                "phone": format_phone(state.phone) if state.phone else None,
                "address": state.address,
            },
            "job": {
                "issue": state.issue,
                "slot_start": start.isoformat() if start else None,
                "diagnostic_fee_usd": self.config.diagnostic_fee_usd,
            },
            "reason": reason,
        }

    def _capture_events(self, state: SessionState, event_name: str) -> list[dict]:
        return [
            {"type": "lead", "payload": _lead_payload(state, state.outcome or event_name)},
            {"type": "webhook", "payload": self._webhook(state, event_name, None)},
        ]

    def _confirm_line(self, state: SessionState, moment: datetime) -> str:
        where = state.address or "the service address"
        return f"Should I lock that in for {format_slot(moment)} at {where}?"

    def _offered(self, state: SessionState) -> list[datetime]:
        return [datetime.fromisoformat(value) for value in state.offered]

    def _area(self, state: SessionState) -> str:
        if state.zip:
            return "ok" if state.zip in self.config.zips else "no"
        if state.city:
            return "ok" if state.city in self.config.cities else "no"
        return "unknown"

    def _finish(
        self,
        state: SessionState,
        say: str,
        started: float,
        events: list[dict] | None = None,
    ) -> TurnResult:
        fresh = events or []
        state.events.extend(fresh)
        elapsed = (perf_counter() - started) * 1000
        return TurnResult(say=say, events=fresh, latency_ms=elapsed)


def _compose_address(street: str, city: str | None, zip_code: str | None) -> str:
    tail = " ".join(bit for bit in (city, zip_code) if bit)
    if tail:
        return f"{street}, {tail}"
    return street


def _choice_fits(choice: datetime | None, preference) -> bool:
    if choice is None:
        return False
    if preference.day is not None and choice.date() != preference.day.date():
        return False
    if preference.part == "morning" and choice.hour >= 12:
        return False
    if preference.part == "afternoon" and not (12 <= choice.hour < 16):
        return False
    if preference.part == "evening" and choice.hour < 16:
        return False
    return True


def _lead_payload(state: SessionState, status: str) -> dict:
    return {
        "id": "ld_" + uuid4().hex[:10],
        "call_id": state.call_id,
        "name": state.name,
        "phone": format_phone(state.phone) if state.phone else None,
        "address": state.address,
        "issue": state.issue,
        "intent": state.intent,
        "status": status,
    }


def summarize(state: SessionState) -> str:
    labels = {
        "new_job": "New job",
        "emergency": "Emergency",
        "quote": "Quote",
        "existing_booking": "Existing booking",
        "spam": "Spam",
        "handoff": "Handoff",
        "unclear": "Unclear",
    }
    parts = []
    if state.intent:
        parts.append(labels.get(state.intent, state.intent))
    if state.issue:
        parts.append(state.issue)
    if state.name:
        parts.append(state.name)
    if state.outcome:
        parts.append(state.outcome.replace("_", " "))
    return " · ".join(parts) or "Call in progress"
