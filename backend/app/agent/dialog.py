"""Claude tool-calling dialog. Facts the caller hears are rendered here.

The model picks an intent and an empathy_id from a fixed list. It does not
write a sentence the caller hears. Booking requires a clear yes to the
server's read-back of that exact slot. record_caller stores only values taken
from the caller's own turns. The model's hazard opinion can raise urgency
only when the local classifier is already asking and the label is a hazard.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from time import monotonic, perf_counter

from app.agent.engine import Engine, SessionState, TurnResult
from app.agent.hazard import _RANK, mentions_hazard_noun, plain_job_text
from app.agent.nlu import (
    detect_language,
    extract_city,
    extract_phone,
    extract_street,
    extract_unit,
    extract_zip,
    extract_caller_name,
    format_phone,
    is_clean_yes,
    wants_human,
)
from app.agent.scheduling import available_slots, format_slot, join_slots, match_offered, parse_preference
from app.agent.understand import assess_caller_turn, understand_enabled
from app.agent.speech import EMPATHY_IDS, FIELDS, INTENTS, render

TOOL_SPECS = [
    {
        "name": "record_caller",
        "description": "Store name, phone, and address only when they appear in the caller's own words. The server ignores anything the caller did not say.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "phone": {"type": "string"},
                "address": {"type": "string"},
                "unit": {"type": "string"},
            },
            "required": ["name", "phone", "address"],
        },
    },
    {
        "name": "find_slots",
        "description": "List open appointment windows. Pass the caller's preference in their words, or empty for the earliest.",
        "input_schema": {
            "type": "object",
            "properties": {"preference": {"type": "string"}},
            "required": ["preference"],
        },
    },
    {
        "name": "hold_slot",
        "description": "Hold one offered slot when the caller's latest words pick that window. Same-turn booking is refused.",
        "input_schema": {
            "type": "object",
            "properties": {"slot_id": {"type": "string"}},
            "required": ["slot_id"],
        },
    },
    {
        "name": "book",
        "description": "Book only after the caller says a clear yes to the server's read-back of that exact slot on a previous turn.",
        "input_schema": {
            "type": "object",
            "properties": {"slot_id": {"type": "string"}},
            "required": ["slot_id"],
        },
    },
    {
        "name": "lookup_booking",
        "description": "Look up a visit from the last four digits and the day the caller just spoke.",
        "input_schema": {
            "type": "object",
            "properties": {"phone": {"type": "string"}},
            "required": ["phone"],
        },
    },
    {
        "name": "cancel",
        "description": "Cancel only after lookup verified the caller and their latest words are a clear yes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "booking_id": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["booking_id", "confirmed"],
        },
    },
    {
        "name": "transfer",
        "description": "Transfer only when the hazard classifier fired or the caller asked for a person. A sales call must not be transferred.",
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
            "required": ["reason"],
        },
    },
    {
        "name": "speak",
        "description": (
            "Choose the caller-facing intent and an empathy_id. Do not write a sentence. "
            "The server speaks a fixed line for that id and fills every fact."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "enum": list(INTENTS)},
                "field": {"type": "string", "enum": list(FIELDS)},
                "empathy_id": {"type": "string", "enum": list(EMPATHY_IDS)},
            },
            "required": ["intent"],
        },
    },
]

_HAZARD_LABELS = {
    "Gas",
    "Carbon monoxide",
    "Active water",
    "Electrical hazard",
    "Unsafe indoor temperature",
    "Caller said emergency",
    "Hazard signals",
}

_HAZARD_SPEC = {
    "name": "classify_hazard",
    "description": "Classify the utterance. definite pages on-call. ask means someone may be in danger. advice is a chirping detector battery. none is routine.",
    "input_schema": {
        "type": "object",
        "properties": {
            "level": {"type": "string", "enum": ["none", "advice", "ask", "definite"]},
            "label": {"type": "string"},
        },
        "required": ["level"],
    },
}

TURN_BUDGET_S = 8.0
CALL_TIMEOUT_S = 5.0
MAX_ROUNDS = 2
_COMMITTED = {"booked", "rescheduled", "cancelled", "escalated"}


class Dialog:
    def __init__(self, engine: Engine, model) -> None:
        self.engine = engine
        self.model = model

    def handle(self, state: SessionState, text: str) -> TurnResult:
        raw = text or ""
        detected = detect_language(raw)
        if state.language == "en" and detected != "en":
            state.language = detected
        state.turn_selected = state.selected if state.phase == "confirm" else None
        local = assess_caller_turn(raw)
        remote = ("none", None)
        if (
            not understand_enabled()
            and self.model is not None
            and _RANK.get(local[0], 0) >= _RANK["ask"]
            and local[0] != "definite"
        ):
            remote = _claude_hazard(self.model, raw)
        level, label = _raise_hazard(local, remote)
        if (
            level == "definite"
            and label
            and _RANK.get(local[0], 0) >= _RANK["ask"]
        ):
            state.hazard = label
        if (
            state.hazard
            or wants_human(raw)
            or level in {"definite", "ask", "advice"}
            or (
                not understand_enabled()
                and mentions_hazard_noun(raw)
                and not plain_job_text(raw)
            )
            or state.language != "en"
        ):
            return self.engine.handle(state, raw)
        if self.model is None:
            return self.engine.handle(state, raw)
        try:
            result = self._model_turn(state, raw)
        except Exception:
            result = self.engine.handle(state, raw)
        _remember(state, raw, result.say)
        if result.say:
            state.last_reply = result.say
        return result

    def _model_turn(self, state: SessionState, text: str) -> TurnResult:
        deadline = monotonic() + TURN_BUDGET_S
        summary = {
            "phase": state.phase,
            "name": state.name,
            "phone": state.phone,
            "address": state.address,
            "issue": state.issue,
            "offered": list(state.offered),
            "selected": state.selected,
            "verified": state.verified,
            "language": state.language,
        }
        messages = list(state.messages)[-6:]
        messages.append(
            {
                "role": "user",
                "content": "STATE " + json.dumps(summary) + "\nCALLER (untrusted): " + json.dumps(text),
            }
        )
        tool_say = ""
        committed: TurnResult | None = None
        speak_failed = False
        rendered: str | None = None
        for _ in range(MAX_ROUNDS):
            remaining = deadline - monotonic()
            if remaining <= 0.3:
                break
            response = self.model.complete(messages, TOOL_SPECS, timeout=min(CALL_TIMEOUT_S, remaining))
            content = response.get("content") or []
            messages.append({"role": "assistant", "content": content})
            tool_uses = [block for block in content if block.get("type") == "tool_use"]
            if any(block.get("name") == "follow_rules" for block in tool_uses):
                return self.engine.handle(state, text)
            if not tool_uses:
                break
            results = []
            for call in tool_uses:
                payload, spoken, result = self._execute(state, text, call.get("name"), call.get("input") or {})
                if spoken:
                    tool_say = spoken
                if result is not None and state.outcome in _COMMITTED:
                    committed = result
                if payload.get("speak_rejected"):
                    speak_failed = True
                if payload.get("rendered"):
                    rendered = str(payload["rendered"])
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call.get("id") or "tool",
                        "content": json.dumps(payload),
                    }
                )
            messages.append({"role": "user", "content": results})
            if state.hazard or state.outcome in _COMMITTED:
                break
        if state.hazard:
            return self.engine._escalate(state, perf_counter(), state.hazard)
        if committed is not None:
            return committed
        if speak_failed:
            return self.engine.handle(state, text)
        if rendered:
            return TurnResult(say=rendered, events=[], latency_ms=0.0)
        if tool_say:
            return TurnResult(say=tool_say, events=list(state.events[-4:]), latency_ms=0.0)
        return self.engine.handle(state, text)

    def _execute(self, state: SessionState, utterance: str, name: str, payload: dict) -> tuple[dict, str, TurnResult | None]:
        if name == "record_caller":
            return self._record(state, utterance, payload)
        if name == "find_slots":
            body, say = self._find_slots(state, str(payload.get("preference") or utterance))
            return body, say, None
        if name == "hold_slot":
            body, say = self._hold(state, utterance, str(payload.get("slot_id") or ""))
            return body, say, None
        if name == "book":
            slot_id = str(payload.get("slot_id") or "")
            if not _booking_consented(state, utterance, slot_id):
                say = "I need a clear yes to the time I just read back before I book it."
                return {"ok": False, "error": "The caller has not agreed to that exact slot."}, say, None
            result = self.engine._book(
                state,
                perf_counter(),
                reschedule=bool(state.verified and state.pending_action == "reschedule"),
            )
            booked = state.outcome in {"booked", "rescheduled"}
            return {"ok": booked, "booked": booked, "say": result.say, "booking_id": state.booking_id}, result.say, result
        if name == "lookup_booking":
            result = self.engine._existing(state, utterance, perf_counter())
            return {"say": result.say, "verified": state.verified}, result.say, result if state.outcome in _COMMITTED else None
        if name == "cancel":
            if not state.verified or not state.booking_id or not is_clean_yes(utterance):
                say = "I need the last four digits, the visit day, and a clear yes before I cancel anything."
                return {"ok": False, "error": "Cancel needs a verified visit and a clear yes from the caller."}, say, None
            result = self.engine._cancel_booking(state, perf_counter())
            return {"ok": True, "say": result.say}, result.say, result
        if name == "transfer":
            allowed = bool(state.hazard or wants_human(utterance))
            if not allowed:
                return {"ok": False, "error": "Transfer is only for a hazard or a caller who asked for a person."}, "", None
            reason = state.hazard or "Caller requested a person"
            result = self.engine._escalate(state, perf_counter(), reason)
            return {"ok": True, "say": result.say, "reason": reason}, result.say, result
        if name == "speak":
            return self._speak(state, utterance, payload)
        return {"error": "unknown tool"}, "", None

    def _speak(self, state: SessionState, utterance: str, payload: dict) -> tuple[dict, str, None]:
        intent = str(payload.get("intent") or "")
        field = payload.get("field")
        empathy_id = payload.get("empathy_id") if isinstance(payload.get("empathy_id"), str) else None
        facts = self._facts(state, utterance)
        spoken = render(intent, field if isinstance(field, str) else None, empathy_id, facts)
        if spoken is None:
            return {"ok": False, "speak_rejected": True, "error": "That line cannot be spoken."}, "", None
        if intent == "ask_field" and isinstance(field, str):
            state.asked_field = field
        return {"ok": True, "rendered": spoken, "say": spoken}, spoken, None

    def _facts(self, state: SessionState, utterance: str) -> dict:
        windows = ""
        if state.offered:
            windows = join_slots([datetime.fromisoformat(item) for item in state.offered])
        moment = self.engine._selected(state)
        allowed = bool(state.hazard or wants_human(utterance))
        return {
            "language": state.language,
            "business": self.engine.config.name,
            "agent": self.engine.config.agent_name,
            "windows": windows,
            "when": format_slot(moment) if moment else "",
            "address": state.address or "",
            "phone_display": format_phone(state.phone) if state.phone else "",
            "quote": self.engine._quote_line(state),
            "transfer_allowed": allowed,
            "on_call": self.engine.config.on_call_name,
        }

    def _record(self, state: SessionState, utterance: str, payload: dict) -> tuple[dict, str, None]:
        del payload
        turns = _caller_turns(state, utterance)
        name = extract_caller_name(turns, state.asked_field, utterance)
        phone = _first(turns, lambda text: extract_phone(text)[0])
        cities = self.engine.config.cities
        street = extract_street(utterance, cities, answering=state.asked_field == "address")
        if not street:
            street = _first(turns, lambda text: extract_street(text, cities))
        unit = _first(turns, extract_unit)
        if street and unit and unit.lower() not in street.lower():
            street = f"{street} {unit}"
        found_zip = _first(turns, extract_zip)
        city = _first(turns, lambda text: extract_city(text, self.engine.config.cities))
        if name:
            state.name = name
        if phone:
            state.phone = phone
        if street:
            state.street = street
        if found_zip:
            state.zip = found_zip
        if city and not state.city:
            state.city = city
        if state.street:
            state.address = _compose(state.street, state.city, state.zip)
        missing = []
        if not state.name:
            missing.append("name")
        if not state.phone:
            missing.append("phone")
        if not state.street:
            missing.append("address")
        facts = {"language": state.language, "business": self.engine.config.name, "agent": self.engine.config.agent_name}
        if missing:
            field = {"name": "name", "phone": "phone", "address": "address"}[missing[0]]
            spoken = render("ask_field", field, None, facts)
            return {"ok": False, "missing": missing, "say": spoken}, spoken or "", None
        follow = render("ask_field", "time", None, facts) or ""
        spoken = f"{_read_back(state)} {follow}".strip()
        return {"ok": True, "name": state.name, "phone": state.phone, "address": state.address, "say": spoken}, spoken, None

    def _find_slots(self, state: SessionState, preference_text: str) -> tuple[dict, str]:
        preference = parse_preference(preference_text, self.engine.now)
        slots, _relaxed = available_slots(
            self.engine.config,
            self.engine.now,
            self.engine.calendar.busy(),
            preference=preference,
            limit=3,
        )
        state.offered = [slot.isoformat() for slot in slots]
        facts = self._facts(state, preference_text)
        spoken = render("offer_slots", None, None, facts)
        if spoken is None:
            spoken = "I don't have an open window in that range."
        payload = {"slots": [{"id": slot.isoformat(), "label": format_slot(slot)} for slot in slots], "say": spoken}
        return payload, spoken

    def _hold(self, state: SessionState, utterance: str, slot_id: str) -> tuple[dict, str]:
        refusal = self._refuse_slot(state, slot_id)
        if refusal:
            return {"ok": False, "error": refusal[0]["error"]}, refusal[1]
        if not _utterance_picks(state, utterance, slot_id, self.engine.now):
            return (
                {"ok": False, "error": "The caller has not picked that window."},
                "Which of the windows I offered should I hold?",
            )
        state.selected = slot_id
        state.phase = "confirm"
        facts = self._facts(state, "")
        spoken = render("confirm_booking", None, None, facts)
        if spoken is None:
            moment = self.engine._selected(state)
            spoken = self.engine._confirm_line(state, moment) if moment else "Which window?"
        return {"ok": True, "slot_id": slot_id, "say": spoken}, spoken

    def _refuse_slot(self, state: SessionState, slot_id: str) -> tuple[dict, str] | None:
        if slot_id not in state.offered:
            return {"ok": False, "error": "That slot was not offered by find_slots."}, "That window is not one I offered."
        if not _customer_ready(self.engine, state):
            return (
                {"ok": False, "error": "Name, phone, and an in-area address are required."},
                "I still need the name, a 10-digit phone, and a service-area address before I hold a window.",
            )
        return None


def _compose(street: str, city: str | None, zip_code: str | None) -> str:
    tail = " ".join(bit for bit in (city, zip_code) if bit)
    if tail:
        return f"{street}, {tail}"
    return street


def _read_back(state: SessionState) -> str:
    phone = format_phone(state.phone)
    if state.language == "es":
        return f"Tengo a {state.name}, teléfono {phone}, en {state.address}."
    return f"I have {state.name}, phone {phone}, at {state.address}."


def _customer_ready(engine: Engine, state: SessionState) -> bool:
    digits = "".join(char for char in (state.phone or "") if char.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if not state.name or len(digits) != 10 or not state.address:
        return False
    return engine._area(state) == "ok"


def _claude_hazard(model, text: str) -> tuple[str, str | None]:
    """Ask the model to classify. Unparseable output counts as no hazard."""
    try:
        response = model.complete(
            [
                {
                    "role": "user",
                    "content": "Classify this caller utterance for a plumbing and HVAC desk. Call classify_hazard only.\nUTTERANCE: "
                    + json.dumps(text),
                }
            ],
            [_HAZARD_SPEC],
            timeout=2.5,
        )
    except Exception:
        return "none", None
    for block in response.get("content") or []:
        if block.get("type") == "tool_use" and block.get("name") == "classify_hazard":
            payload = block.get("input") or {}
            level = str(payload.get("level") or "none")
            if level not in {"none", "advice", "ask", "definite"}:
                return "none", None
            label = payload.get("label")
            return level, label if isinstance(label, str) and label else None
    return "none", None


def _caller_turns(state: SessionState, utterance: str) -> list[str]:
    turns = [str(message.get("content") or "") for message in state.messages if message.get("role") == "user"]
    turns.append(utterance or "")
    return [turn for turn in turns if turn.strip()]


def _first(turns: list[str], reader):
    for turn in reversed(turns):
        found = reader(turn)
        if found:
            return found
    return None


def _utterance_picks(state: SessionState, utterance: str, slot_id: str, now: datetime) -> bool:
    if slot_id not in state.offered:
        return False
    offered = [datetime.fromisoformat(item) for item in state.offered]
    target = datetime.fromisoformat(slot_id)
    choice = match_offered(offered, utterance)
    if choice is not None and choice.isoformat() == slot_id:
        return True
    norm = (utterance or "").lower()
    index = state.offered.index(slot_id)
    if index == 0 and re.search(r"\b(first|earliest|soonest)\b", norm):
        return True
    if index == 1 and re.search(r"\bsecond\b", norm):
        return True
    if index == 2 and re.search(r"\b(third|last)\b", norm):
        return True
    preference = parse_preference(utterance, now)
    if preference is not None and preference.around is not None:
        if target.hour == preference.around.hour and abs(target.minute - preference.around.minute) <= 30:
            return True
    clock = target.hour % 12 or 12
    if re.search(rf"\b{clock}\b", norm) and re.search(r"\b(o'clock|oclock|am|pm)\b", norm):
        return True
    return False


def _booking_consented(state: SessionState, utterance: str, slot_id: str) -> bool:
    if state.phase != "confirm" or not slot_id or state.selected != slot_id:
        return False
    if getattr(state, "turn_selected", None) != slot_id:
        return False
    if not is_clean_yes(utterance):
        return False
    reply = state.last_reply or ""
    try:
        moment = datetime.fromisoformat(slot_id)
    except ValueError:
        return False
    label = format_slot(moment)
    return label in reply or (format_slot(moment).split(" at ")[0] in reply and str(moment.hour % 12 or 12) in reply)


def _raise_hazard(local: tuple[str, str | None], remote: tuple[str, str | None]) -> tuple[str, str | None]:
    """The model may raise an ask to a definite hazard. It cannot create one."""
    if _RANK.get(local[0], 0) < _RANK["ask"]:
        return local
    if _RANK.get(remote[0], 0) <= _RANK.get(local[0], 0):
        return local
    if remote[1] not in _HAZARD_LABELS:
        return local
    return remote


def _remember(state: SessionState, caller: str, reply: str) -> None:
    state.messages.append({"role": "user", "content": caller})
    state.messages.append({"role": "assistant", "content": reply})
    if len(state.messages) > 8:
        state.messages = state.messages[-8:]
