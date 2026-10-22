"""Rule-based receptionist. Safe to run with no paid API keys."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from time import perf_counter
from uuid import uuid4

from app.agent.calendar import Calendar, SlotTaken, new_booking_id
from app.agent.nlu import (
    caller_id_digits,
    classify_emergency,
    detect_intent,
    extract_city,
    extract_issue,
    extract_phone,
    extract_street,
    extract_zip,
    format_phone,
    detect_language,
    fallback_name,
    guess_bare_name,
    house_correction,
    last4_correction,
    is_correction,
    is_haggle,
    is_clean_yes,
    is_no,
    is_spam,
    is_yes,
    safety_decision,
    spelled_word,
    wants_abandon,
    wants_cancel,
    wants_human,
    wants_reschedule,
)
from app.agent.scheduling import available_slots, format_slot, join_slots, latest_on_day, match_offered, parse_preference
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
    caller_id: str | None = None
    language: str = "en"
    silence_count: int = 0
    wish: str | None = None
    last_caller_text: str | None = None
    last_reply: str | None = None
    hazard: str | None = None
    verified: bool = False
    verify_last4: str | None = None
    verify_day: str | None = None
    verify_fails: int = 0
    unclear_count: int = 0
    asked_field: str | None = None
    name_rejects: int = 0
    name_confidence: str | None = None
    address_from_prompt: bool = False
    address_read_back: bool = False
    degraded_asked: bool = False
    safety_reasks: int = 0
    messages: list = field(default_factory=list)
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


_BATTERY_EN = (
    "If a carbon monoxide alarm is sounding, leave the house and call 911. "
    "A single chirp is often a low battery, and I can still schedule a technician."
)
_BATTERY_ES = (
    "Si la alarma de monóxido está sonando, salga de la casa y llame al 911. "
    "Un solo pitido suele ser la pila, y puedo agendar una visita."
)
_ASK_EN = "Is anyone in danger right now? I can connect you to the on-call technician."
_ASK_ES = "¿Hay alguien en peligro ahora mismo? Puedo comunicarlo con el técnico de guardia."


def _looks_like_verification(text: str) -> bool:
    has_pin = bool(re.search(r"\b\d{4}\b", text or "")) or len(re.sub(r"\D", "", text or "")) >= 10
    has_day = bool(
        re.search(
            r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today|"
            r"january|february|march|april|may|june|july|august|september|october|november|december)\b",
            text or "",
            re.I,
        )
    )
    return has_pin and has_day and "earliest" not in (text or "").lower()


class Engine:
    def __init__(self, config: BusinessConfig, calendar: Calendar, clock) -> None:
        self.config = config
        self.calendar = calendar
        self.clock = clock
        self.sms_sender = None
        self._sms_delivery = "not_sent"
        self.verify_fails_by_key: dict[str, int] = {}

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
            state.silence_count += 1
            if state.silence_count >= 3:
                state.outcome = "missed"
                state.phase = "closed"
                return self._finish(
                    state,
                    "I still can't hear you. Please call back when you can. Goodbye.",
                    started,
                )
            return self._finish(state, "I didn't catch that. What's going on at the property?", started)
        state.silence_count = 0
        if state.phase == "closed":
            if state.booking_id and state.last_reply and raw == (state.last_caller_text or ""):
                return self._finish(state, state.last_reply, started)
            return self._finish(
                state,
                "This call has ended. Please call back if something else comes up.",
                started,
            )

        detected = detect_language(raw)
        if state.language == "en" and detected != "en":
            state.language = detected

        if state.phase == "hazard_check":
            return self._answer_hazard_check(state, raw, started)
        if state.phase == "unclear_handoff":
            return self._unclear_handoff(state, raw, started)

        if state.hazard:
            return self._escalate(state, started, state.hazard)

        level, emergency = classify_emergency(raw)
        if level == "ask" and emergency == "Hazard model unavailable":
            if state.degraded_asked:
                level, emergency = "none", None
            else:
                state.degraded_asked = True
        if level == "definite" and emergency:
            self._fill(state, raw)
            state.intent = "emergency"
            state.issue = emergency
            state.hazard = emergency
            return self._escalate(state, started, emergency)
        if level == "ask":
            self._fill(state, raw)
            state.phase = "hazard_check"
            state.issue = state.issue or emergency
            return self._finish(state, self._line(state, _ASK_EN, _ASK_ES), started)
        if level == "advice":
            self._fill(state, raw)
            state.issue = state.issue or "CO detector battery"
            if state.language != "en":
                return self._language_handoff(state, started, prefix=self._line(state, _BATTERY_EN, _BATTERY_ES))
            return self._finish(state, self._line(state, _BATTERY_EN, _BATTERY_ES), started)

        if state.language != "en":
            self._fill(state, raw)
            return self._language_handoff(state, started)

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
            if state.intent in {"new_job", "quote"} and not state.issue:
                cleaned = " ".join(raw.split())
                if len(cleaned.split()) >= 3 and not is_spam(cleaned):
                    state.issue = cleaned[:80].rstrip(".")
            if state.intent == "unclear":
                state.unclear_count += 1
                if state.unclear_count > 2:
                    state.phase = "unclear_handoff"
                    return self._finish(
                        state,
                        "Is anyone in danger, or would you like a person to call you back?",
                        started,
                    )
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
            return self._existing(state, raw, started)

        if state.phase == "existing_action":
            self._fill(state, raw)
            return self._existing(state, raw, started)

        if state.phase in {"collect_issue", "collect_name", "collect_phone", "collect_address", "collect_zip"}:
            self._fill(state, raw)
            if state.phase == "collect_issue" and not state.issue:
                return self._finish(
                    state,
                    self._line(state, "Tell me a bit more about what's going wrong.", "Cuénteme un poco más qué está fallando."),
                    started,
                )
            if state.phase == "collect_name" and not state.name:
                state.name_rejects += 1
                if state.name_rejects >= 2:
                    state.name = fallback_name(raw)
                    state.name_confidence = "low"
                    return self._continue_intake(state, raw, started)
                return self._finish(
                    state,
                    self._line(state, "Sorry, I missed the name. Who am I speaking with?", "Perdón, no escuché el nombre. ¿Con quién hablo?"),
                    started,
                )
            if state.phase == "collect_phone" and not state.phone:
                return self._finish(
                    state,
                    self._line(
                        state,
                        "I still need a phone number. What's the best number for the technician?",
                        "Todavía necesito un teléfono. ¿Cuál es el mejor número para el técnico?",
                    ),
                    started,
                )
            if state.phase == "collect_address" and not state.street:
                return self._finish(
                    state,
                    self._line(
                        state,
                        "I still need the street address. What's the house number and street?",
                        "Todavía necesito la calle. ¿Cuál es el número y la calle?",
                    ),
                    started,
                )
            if state.phase == "collect_zip" and self._area(state) == "unknown":
                return self._finish(
                    state,
                    self._line(state, "Which ZIP code is the property in?", "¿Cuál es el código postal de la propiedad?"),
                    started,
                )
            return self._continue_intake(state, raw, started)

        if state.phase == "quote_decision":
            self._fill(state, raw)
            if is_no(raw) and not is_yes(raw):
                return self._decline_quote(state, started)
            if is_yes(raw) or state.name or state.phone:
                return self._continue_intake(state, raw, started)
            return self._finish(state, self._quote_line(state) + " Should I book the diagnostic?", started)

        if state.phase == "offer":
            self._fill(state, raw)
            return self._on_offer(state, raw, started)

        if state.phase == "confirm_cancel":
            return self._on_confirm_cancel(state, raw, started)

        if state.phase == "confirm":
            self._fill(state, raw)
            return self._on_confirm(state, raw, started)

        return self._finish(
            state,
            "I can help with a new repair, an estimate, an existing appointment, or an emergency. What's going on?",
            started,
        )

    def _fill(self, state: SessionState, text: str) -> None:
        if not state.caller_id:
            pass
        phone, _ = extract_phone(text)
        last4 = last4_correction(text)
        if last4 and state.phone:
            state.phone = state.phone[:-4] + last4
        elif phone and (not state.phone or is_correction(text)):
            state.phone = phone
        house = house_correction(text)
        if house and state.street and house[1] in state.street:
            state.street = state.street.replace(house[1], house[0], 1)
            state.address = _compose_address(state.street, state.city, state.zip)
        found_zip = extract_zip(text)
        if found_zip and (not state.zip or is_correction(text)):
            state.zip = found_zip
        if not state.city:
            city = extract_city(text, self.config.cities)
            if city:
                state.city = city
        street = None if last4 else extract_street(
            text,
            self.config.cities,
            answering=state.phase == "collect_address",
        )
        if street and (not state.street or is_correction(text) or house):
            state.street = street
            if state.phase == "collect_address":
                state.address_from_prompt = True
        if state.street:
            state.address = _compose_address(state.street, state.city, state.zip)
        issue = extract_issue(text)
        if issue and not state.issue:
            state.issue = issue
        elif not state.issue and re.search(r"\b(inspect\w*|checked)\b", text, re.I):
            state.issue = "Inspection"
        spelled = spelled_word(text)
        if state.name and is_correction(text):
            parts = state.name.split()
            replacement = spelled
            meant = re.search(r"\b(?:it's|its|meant)\s+([^\W\d_](?:[^\W\d_]|['-])+)\b", text, re.I)
            if replacement is None and meant and meant.group(1).lower() not in {"the", "a", "my"}:
                replacement = meant.group(1).capitalize()
            if replacement and parts:
                parts[-1] = replacement
                state.name = " ".join(parts)
        elif not state.name or (is_correction(text) and guess_bare_name(text, framed=True)):
            framed = state.phase == "collect_name" or state.asked_field == "name"
            guessed = guess_bare_name(text, framed=framed)
            if guessed and (state.phase == "collect_name" or not state.name or is_correction(text)):
                if state.phase == "collect_name" or is_correction(text) or " " in guessed:
                    if not state.name or is_correction(text) or state.phase == "collect_name":
                        state.name = guessed
        if state.phase == "collect_issue" and not state.issue:
            cleaned = " ".join(text.split())
            if len(cleaned.split()) >= 3 and not is_spam(cleaned):
                state.issue = cleaned[:80].rstrip(".")

    def _continue_intake(self, state: SessionState, text: str, started: float) -> TurnResult:
        if not state.issue:
            state.phase = "collect_issue"
            return self._finish(
                state,
                self._line(state, "What seems to be the problem at the property?", "¿Qué problema hay en la propiedad?"),
                started,
            )
        if state.intent == "quote" and not state.quote_given:
            state.quote_given = True
            state.wish = text
            state.phase = "quote_decision"
            return self._finish(
                state,
                self._quote_line(state) + " Want me to book a diagnostic visit?",
                started,
            )
        if not state.name:
            state.phase = "collect_name"
            state.asked_field = "name"
            return self._finish(
                state,
                self._line(
                    state,
                    "Who am I speaking with? Can I get your first and last name?",
                    "¿Con quién hablo? ¿Su nombre y apellido?",
                ),
                started,
            )
        if not state.phone:
            state.phase = "collect_phone"
            return self._finish(
                state,
                self._line(
                    state,
                    "What's the best phone number for the technician?",
                    "¿Cuál es el mejor teléfono para el técnico?",
                ),
                started,
            )
        if not state.street:
            state.phase = "collect_address"
            return self._finish(
                state,
                self._line(state, "What's the street address?", "¿Cuál es la dirección?"),
                started,
            )
        if self._area(state) == "unknown":
            state.phase = "collect_zip"
            return self._finish(
                state,
                self._address_prefix(state)
                + self._line(state, "Which ZIP code is the property in?", "¿Cuál es el código postal de la propiedad?"),
                started,
            )
        if self._area(state) == "no":
            return self._out_of_area(state, started)
        return self._offer(state, text, started)

    def _offer(self, state: SessionState, text: str, started: float) -> TurnResult:
        if state.hazard:
            return self._escalate(state, started, state.hazard)
        preference = parse_preference(text, self.now)
        if preference is not None and preference.unresolved:
            state.phase = "offer"
            state.offered = []
            state.selected = None
            return self._finish(state, "Which day did you mean?", started)
        if preference is not None and preference.day is not None:
            last = self.now + timedelta(days=self.config.horizon_days)
            if preference.day.date() > last.date():
                named = f"{preference.day.strftime('%A, %B')} {preference.day.day}"
                label = f"{last.strftime('%A, %B')} {last.day}"
                state.phase = "offer"
                state.offered = []
                state.selected = None
                return self._finish(
                    state,
                    f"{named} is past my booking window. I can book up to {label}. What day before then works?",
                    started,
                )
        if preference is not None:
            state.wish = text
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
        if relaxed and preference is not None and preference.earliest is not None and preference.day is not None:
            latest = latest_on_day(self.config, self.now, self.calendar.busy(), preference.day)
            if latest is not None:
                state.offered = [latest.isoformat()]
                state.selected = latest.isoformat()
                state.phase = "confirm"
                return self._finish(
                    state,
                    f"Nothing starts after {preference.label.split('after ')[-1]}. "
                    f"The latest window is {format_slot(latest)}. Should I lock that in?",
                    started,
                )
        state.offered = [slot.isoformat() for slot in slots]
        choice = match_offered(slots, text)
        if preference is not None and preference.around is not None and choice is None:
            choice = slots[0]
        prefix = self._address_prefix(state)
        if relaxed and preference is not None:
            prefix += f"I don't have a {preference.label} opening. The next open windows are different. "
        if choice is not None and (preference is None or _choice_fits(choice, preference)):
            state.selected = choice.isoformat()
            state.phase = "confirm"
            return self._finish(state, prefix + self._confirm_line(state, choice), started)
        state.selected = None
        state.phase = "offer"
        english = f"{prefix}I can come {join_slots(slots)}. Which works best?"
        spanish = f"Puedo ir {join_slots(slots)}. ¿Cuál le queda?"
        return self._finish(state, self._line(state, english, spanish), started)

    def _on_offer(self, state: SessionState, text: str, started: float) -> TurnResult:
        note = ""
        house = house_correction(text)
        if house and house[0] in (state.address or ""):
            note = f"I have the house number as {house[0]}. "
        preference = parse_preference(text, self.now)
        offered = self._offered(state)
        choice = match_offered(offered, text)
        if preference is not None and not _choice_fits(choice, preference):
            return self._offer(state, text, started)
        if choice is None:
            return self._finish(
                state,
                f"{note}I have {join_slots(offered)}. Which of those works?",
                started,
            )
        state.selected = choice.isoformat()
        state.phase = "confirm"
        return self._finish(state, note + self._confirm_line(state, choice), started)

    def _on_confirm(self, state: SessionState, text: str, started: float) -> TurnResult:
        if house_correction(text) and state.address:
            moment = self._selected(state)
            if moment is not None:
                return self._finish(state, self._confirm_line(state, moment), started)
        offered = self._offered(state)
        preference = parse_preference(text, self.now)
        if preference is not None and (is_correction(text) or not _choice_fits(self._selected(state), preference)):
            return self._offer(state, text, started)
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

    def _on_confirm_cancel(self, state: SessionState, text: str, started: float) -> TurnResult:
        if wants_reschedule(text) or (
            re.search(r"\b(actually|instead|move)\b", text, re.I) and parse_preference(text, self.now) is not None
        ):
            state.pending_action = "reschedule"
            state.wish = text
            state.phase = "existing_action"
            return self._existing(state, text, started)
        if is_clean_yes(text) and state.verified and state.booking_id:
            return self._cancel_booking(state, started)
        if is_no(text) and not is_yes(text):
            state.phase = "closed"
            state.outcome = "kept"
            state.pending_action = None
            return self._finish(state, "I'll leave that visit on the calendar. Call us if you need a new time.", started)
        return self._finish(
            state,
            "I didn't take that as a yes. Should I cancel that visit? Please say yes or no, with no extra question.",
            started,
        )

    def _book(self, state: SessionState, started: float, reschedule: bool) -> TurnResult:
        if state.hazard:
            return self._escalate(state, started, state.hazard)
        if state.booking_id and not reschedule and state.outcome == "booked":
            start = datetime.fromisoformat(state.selected) if state.selected else self.now
            return self._finish(
                state,
                f"You're already booked for {format_slot(start)} at {state.address}.",
                started,
            )
        if not state.selected:
            return self._offer(state, state.wish or "", started)
        start = datetime.fromisoformat(state.selected)
        end = start + timedelta(minutes=self.config.slot_minutes)
        try:
            if reschedule and state.booking_id:
                record = self.calendar.reschedule(state.booking_id, start, end)
                outcome = "rescheduled"
                event_name = "job.rescheduled"
                say = (
                    f"You're moved to {format_slot(start)} at {state.address}. "
                    f"{self._notice(state, start, outcome)}"
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
                fee = f"The diagnostic visit is ${self.config.diagnostic_fee_usd} and we waive it if you approve the repair."
                if self._after_hours(self.now):
                    fee += f" Because you called after hours, the trip fee is ${self.config.after_hours_fee_usd}."
                say = (
                    f"You're booked for {format_slot(start)} at {state.address}. "
                    f"{self._notice(state, start, 'booked')} "
                    f"{fee}"
                )
        except SlotTaken:
            state.selected = None
            state.phase = "offer"
            slots, _ = available_slots(self.config, self.now, self.calendar.busy(), limit=3)
            state.offered = [slot.isoformat() for slot in slots]
            if not slots:
                return self._finish(state, "That time was just taken, and I don't have another window this week.", started)
            return self._finish(
                state,
                f"That time was just taken. I can come {join_slots(slots)}. Which works best?",
                started,
            )
        state.outcome = outcome
        state.phase = "closed"
        events = [
            {"type": "booking", "payload": record},
            {"type": "lead", "payload": _lead_payload(state, outcome)},
            {"type": "sms", "payload": {"to": state.phone, "body": self._sms(state, start, outcome), "delivery": self._sms_delivery}},
            {"type": "webhook", "payload": self._webhook(state, event_name, start)},
        ]
        return self._finish(state, say, started, events)

    def _existing(self, state: SessionState, text: str, started: float) -> TurnResult:
        state.intent = "existing_booking"
        if wants_cancel(text) and not wants_reschedule(text):
            state.pending_action = "cancel"
        elif wants_reschedule(text):
            state.pending_action = "reschedule"
        if "earliest" in text.lower() or (
            parse_preference(text, self.now) is not None and not _looks_like_verification(text)
        ):
            state.wish = text
        self._note_verification(state, text)
        if not state.verified:
            state.phase = "existing_lookup"
            locked = self._blocked_booking(state)
            if locked is not None:
                return self._lockout(state, started, locked, alert=False)
            found = self._verified_booking(state)
            if found is None:
                if state.verify_last4 and state.verify_day:
                    state.verify_day = None
                    return self._failed_verify(state, started)
                return self._finish(
                    state,
                    self._line(
                        state,
                        "I need the last four digits of the phone on the visit, and the day it is scheduled. "
                        "I won't read the address before those match.",
                        "Necesito los últimos cuatro dígitos del teléfono de la visita y el día. "
                        "No leo la dirección antes de que coincidan.",
                    ),
                    started,
                )
            self._adopt(state, found)
        found = self.calendar.find(None, state.phone) if state.phone else None
        when = format_slot(datetime.fromisoformat(found["start"])) if found else "that visit"
        if state.pending_action == "cancel":
            state.phase = "confirm_cancel"
            return self._finish(
                state,
                f"I found a visit on {when}. I won't read the street. Should I cancel it?",
                started,
            )
        if state.pending_action == "reschedule":
            if not state.wish or _looks_like_verification(state.wish):
                state.phase = "existing_action"
                return self._finish(
                    state,
                    f"You're currently set for {when}. What day and time should I move it to?",
                    started,
                )
            result = self._offer(state, state.wish, started)
            result.say = f"You're currently set for {when}. " + result.say
            return result
        state.phase = "existing_action"
        return self._finish(
            state,
            f"I found a visit on {when}. Do you want to reschedule or cancel?",
            started,
        )

    def _cancel_booking(self, state: SessionState, started: float) -> TurnResult:
        found = self.calendar.find(None, state.phone)
        when = "that visit"
        if found:
            when = format_slot(datetime.fromisoformat(found["start"]))
        cancelled = self.calendar.cancel(state.booking_id or (found or {}).get("id"))
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

    def _blocked_booking(self, state: SessionState) -> dict | None:
        if not state.verify_last4 or not hasattr(self.calendar, "bookings_with_last4"):
            return None
        owners = self.calendar.bookings_with_last4(state.verify_last4)
        if len(owners) != 1 or not hasattr(self.calendar, "verify_status"):
            return None
        status = self.calendar.verify_status(owners[0]["id"], self.now)
        if status.get("hard_lock"):
            return owners[0]
        if status.get("delayed") and state.verify_fails < 1:
            return owners[0]
        return None

    def _failed_verify(self, state: SessionState, started: float) -> TurnResult:
        owners = []
        if hasattr(self.calendar, "bookings_with_last4") and state.verify_last4:
            owners = self.calendar.bookings_with_last4(state.verify_last4)
        if len(owners) != 1 or not hasattr(self.calendar, "record_verify_failure"):
            return self._finish(state, self._verify_miss_line(state), started)
        recorded = self.calendar.record_verify_failure(owners[0]["id"], owners[0].get("phone") or "", self.now)
        state.verify_fails += 1
        if recorded.get("alert"):
            return self._lockout(state, started, owners[0], alert=True)
        return self._finish(state, self._verify_miss_line(state), started)

    def _verify_miss_line(self, state: SessionState) -> str:
        return self._line(
            state,
            "I don't have a visit with those last four digits on that day. "
            "You can try again. I won't read the street.",
            "No tengo una visita con esos cuatro dígitos en ese día. "
            "Puede intentar otra vez. No leo la calle.",
        )

    def _lockout(self, state: SessionState, started: float, booking: dict | None = None, alert: bool = False) -> TurnResult:
        state.outcome = "locked"
        state.phase = "closed"
        say = (
            "I can't verify that visit. I won't cancel it, and I won't read the address. "
            "The office will call the number on the booking."
        )
        events = [
            {
                "type": "verification_failed",
                "payload": {"last4": state.verify_last4, "attempts": state.verify_fails, "booking_id": (booking or {}).get("id")},
            }
        ]
        if alert and booking and booking.get("phone"):
            body = (
                f"{self.config.name}: someone tried to change your visit and could not verify. "
                "We did not cancel it."
            )
            delivery = "not_sent"
            sender = getattr(self, "sms_sender", None)
            if sender:
                result = sender(booking["phone"], body) or {}
                if result.get("status") == "sent":
                    delivery = "sent"
            events.append({"type": "sms", "payload": {"to": booking["phone"], "body": body, "delivery": delivery}})
        result = self._finish(state, say, started, events)
        return result

    def _language_handoff(self, state: SessionState, started: float, prefix: str = "") -> TurnResult:
        state.phase = "closed"
        state.outcome = "qualified"
        state.intent = state.intent or "handoff"
        if state.language == "es":
            say = (
                "No reservo visitas en español. Una persona de la oficina le devolverá la llamada. "
                "Si huele a gas, salga de la casa y llame al 911 o a la compañía de gas."
            )
        else:
            say = (
                "I can't book a visit in this language. A person will call you back. "
                "If you smell gas, leave the house and call 911 or your gas company."
            )
        if prefix:
            say = f"{prefix} {say}"
        return self._finish(state, say, started, self._capture_events(state, "lead.callback"))

    def _safety_answer(self, state: SessionState, raw: str, started: float, *, on_clear: str) -> TurnResult:
        """One decision for both safety questions. Unclear pages. A clean no does not.

        on_clear is 'intake' after a hazard question, or 'callback' after the
        unclear-path question, where a clean no still does not name a job.
        """
        level_now, emergency_now = classify_emergency(raw)
        if level_now == "definite" and emergency_now and emergency_now != "Hazard model unavailable":
            state.hazard = emergency_now
            self._fill(state, raw)
            return self._escalate(state, started, state.hazard)
        decision = safety_decision(raw)
        if decision == "page":
            state.hazard = "Caller confirmed danger"
            self._fill(state, raw)
            return self._escalate(state, started, state.hazard)
        self._fill(state, raw)
        if decision == "callback" or on_clear == "callback":
            return self._office_callback(state, started)
        state.degraded_asked = True
        if state.language != "en":
            return self._language_handoff(state, started)
        state.phase = "discover"
        return self._continue_intake(state, raw, started)

    def _answer_hazard_check(self, state: SessionState, raw: str, started: float) -> TurnResult:
        """A clean no continues intake. Any other answer pages, or transfers warm."""
        return self._safety_answer(state, raw, started, on_clear="intake")

    def _address_prefix(self, state: SessionState) -> str:
        if state.address_from_prompt and state.address and not state.address_read_back:
            state.address_read_back = True
            return f"I have the address as {state.address}. "
        return ""

    def _unclear_handoff(self, state: SessionState, raw: str, started: float) -> TurnResult:
        """The answer to the unclear-path safety question. It does not ask again."""
        return self._safety_answer(state, raw, started, on_clear="callback")

    def _office_callback(self, state: SessionState, started: float) -> TurnResult:
        state.outcome = "callback"
        state.phase = "closed"
        state.intent = state.intent or "handoff"
        say = "A person from the office will call you back. If anyone is in danger, call 911."
        if state.language == "es":
            say = "Una persona de la oficina le devolverá la llamada. Si hay alguien en peligro, llame al 911."
        events = [
            {"type": "lead", "payload": _lead_payload(state, "callback")},
            {"type": "webhook", "payload": self._webhook(state, "lead.callback", None)},
        ]
        return self._finish(state, say, started, events)

    def _escalate(self, state: SessionState, started: float, reason: str) -> TurnResult:
        state.outcome = "escalated"
        state.phase = "closed"
        who = self.config.on_call_name
        if state.language == "es" and _comfort_hazard(reason):
            say = (
                f"Esto es urgente. Lo comunico con {who}, el técnico de guardia. Quédese en la línea. "
                "Mantenga a las personas vulnerables en un lugar tibio o fresco, y llame al 911 si se sienten mal. "
                f"La tarifa de emergencia es ${self.config.emergency_dispatch_usd}."
            )
        elif state.language == "es":
            say = (
                f"Esto es urgente. Lo comunico con {who}, el técnico de guardia. Quédese en la línea. "
                "Si huele a gas, salga de la casa y llame al 911 o a la compañía de gas. "
                f"La tarifa de emergencia es ${self.config.emergency_dispatch_usd}."
            )
        elif reason == "Caller requested a person":
            say = (
                f"You asked for a person, so I'm connecting you to {who}, our on-call technician. "
                "Please stay on the line."
            )
        elif _comfort_hazard(reason):
            say = (
                f"I'm treating this as an emergency and connecting you to {who}, our on-call technician. "
                "Please stay on the line. Keep anyone vulnerable warm or cool, and call 911 if they are unwell. "
                f"The emergency dispatch fee is ${self.config.emergency_dispatch_usd}."
            )
        else:
            say = (
                f"I'm treating this as an emergency and connecting you to {who}, our on-call technician. "
                f"Please stay on the line. If you smell gas, leave the house and call 911 or your gas company. "
                f"The emergency dispatch fee is ${self.config.emergency_dispatch_usd}."
            )
        if state.address and state.address_from_prompt and reason != "Caller requested a person":
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
        policy = ""
        if state.wish and is_haggle(state.wish):
            policy = (
                " That is the standard price. Any discount is the technician's call on site. "
                "We don't match or beat another company's price."
            )
        if rule is None:
            return (
                f"Most visits start with a ${fee} diagnostic fee that we waive if you approve the repair.{policy}"
            )
        return (
            f"For {rule.label.lower()}, jobs typically run ${rule.low_usd:,} to ${rule.high_usd:,}, "
            f"plus a ${fee} diagnostic fee that we waive if you approve the repair.{policy}"
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
        phone = format_phone(state.phone)
        if state.language == "es":
            phone_bit = f" Anoto {phone} en la visita." if phone else ""
            return f"¿Lo dejo para {format_slot(moment)} en {where}?{phone_bit}"
        phone_bit = f" I'll note {phone} on the visit." if phone else ""
        return f"Should I lock that in for {format_slot(moment)} at {where}?{phone_bit}"

    def _selected(self, state: SessionState) -> datetime | None:
        if not state.selected:
            return None
        return datetime.fromisoformat(state.selected)

    def _after_hours(self, moment: datetime) -> bool:
        hours = self.config.hours.get(moment.weekday())
        if hours is None:
            return True
        return not (hours.open <= moment.time() < hours.close)

    def _offered(self, state: SessionState) -> list[datetime]:
        return [datetime.fromisoformat(value) for value in state.offered]

    def _area(self, state: SessionState) -> str:
        if state.zip:
            return "ok" if state.zip in self.config.zips else "no"
        if state.city:
            return "ok" if state.city in self.config.cities else "no"
        return "unknown"

    def _line(self, state: SessionState, english: str, spanish: str) -> str:
        if state.language == "es":
            return spanish
        return english

    def _notice(self, state: SessionState, start: datetime, outcome: str) -> str:
        self._sms_delivery = "not_sent"
        phone = format_phone(state.phone) if state.phone else ""
        sender = getattr(self, "sms_sender", None)
        if sender and state.phone:
            result = sender(state.phone, self._sms(state, start, outcome))
            if result.get("status") == "sent":
                self._sms_delivery = "sent"
                return f"I texted a confirmation to {phone}."
        if phone:
            return f"I have not sent a text to {phone}. The visit is on the board."
        return "I have not sent a text. The visit is on the board."

    def _note_verification(self, state: SessionState, text: str) -> None:
        digits = re.sub(r"\D", "", text)
        groups = re.findall(r"\b(\d{4})\b", text)
        if groups:
            state.verify_last4 = groups[-1]
        elif len(digits) >= 10:
            core = digits[1:] if len(digits) == 11 and digits.startswith("1") else digits[-10:]
            state.verify_last4 = core[-4:]
        if state.verified:
            return
        preference = parse_preference(text, self.now)
        if preference is None or preference.day is None:
            return
        if _looks_like_verification(text) or (
            state.verify_last4 and not re.search(r"\b(afternoon|morning|evening|noon|earliest)\b", text, re.I)
        ):
            state.verify_day = preference.day.date().isoformat()

    def _verified_booking(self, state: SessionState) -> dict | None:
        if not state.verify_last4 or not state.verify_day:
            return None
        matches = self.calendar.match_visit(state.verify_last4, state.verify_day)
        if len(matches) != 1:
            return None
        state.verified = True
        return matches[0]

    def _adopt(self, state: SessionState, found: dict) -> None:
        state.booking_id = found["id"]
        state.name = found.get("name") or state.name
        state.phone = found.get("phone") or state.phone
        state.address = found.get("address") or state.address
        state.issue = state.issue or found.get("issue")

    def _finish(
        self,
        state: SessionState,
        say: str,
        started: float,
        events: list[dict] | None = None,
    ) -> TurnResult:
        fresh = events or []
        state.events.extend(fresh)
        state.last_reply = say
        elapsed = (perf_counter() - started) * 1000
        return TurnResult(say=say, events=fresh, latency_ms=elapsed)


def _compose_address(street: str, city: str | None, zip_code: str | None) -> str:
    tail = " ".join(bit for bit in (city, zip_code) if bit)
    if tail:
        return f"{street}, {tail}"
    return street


def _choice_fits(choice: datetime | None, preference) -> bool:
    if choice is None or preference is None:
        return False
    if preference.day is not None and choice.date() != preference.day.date():
        return False
    if preference.earliest is not None and choice.time() < preference.earliest:
        return False
    if preference.part == "morning" and choice.hour >= 12:
        return False
    if preference.part == "afternoon" and not (12 <= choice.hour < 17):
        return False
    if preference.part == "lunch":
        from datetime import time as clock_time

        if not (clock_time(11, 30) <= choice.time() <= clock_time(13, 30)):
            return False
    if preference.part == "evening" and choice.hour < 16:
        return False
    return True


def _comfort_hazard(reason: str | None) -> bool:
    label = (reason or "").lower()
    return "temperature" in label or "comfort" in label


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
