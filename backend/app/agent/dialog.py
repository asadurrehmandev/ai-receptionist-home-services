"""Claude tool-calling dialog. Facts the caller hears are rendered here.

The model picks an intent from a fixed set and may add a short empathy line.
It does not write clock times, prices, promises, or repair steps. The server
fills those from tool results. A line that fails the empathy check is dropped
and the rules engine speaks instead. A hazard is the stricter of the local
classifier and, when a model is configured, the model's own classification.
"""

from __future__ import annotations

import json
from datetime import datetime
from time import monotonic, perf_counter

from app.agent.engine import Engine, SessionState, TurnResult
from app.agent.hazard import _stricter
from app.agent.nlu import (
    classify_emergency,
    extract_city,
    extract_phone,
    extract_street,
    extract_unit,
    extract_zip,
    format_phone,
    guess_bare_name,
    is_clean_yes,
    looks_spanish,
    wants_human,
)
from app.agent.scheduling import available_slots, format_slot, join_slots, parse_preference
from app.agent.speech import FIELDS, INTENTS, render

TOOL_SPECS = [
    {
        "name": "record_caller",
        "description": "Store the caller's name, phone, street address, and unit after they say them. The server validates and reads them back.",
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
        "description": "Hold one slot id that find_slots returned on this call. Requires the caller's name, phone, and service-area address.",
        "input_schema": {
            "type": "object",
            "properties": {"slot_id": {"type": "string"}},
            "required": ["slot_id"],
        },
    },
    {
        "name": "book",
        "description": "Book a slot id that find_slots returned. Requires name, a 10-digit phone, and an in-area address.",
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
            "Choose the caller-facing intent. Do not put digits, times, prices, promises, "
            "or instructions in empathy. The server writes every fact."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "enum": list(INTENTS)},
                "field": {"type": "string", "enum": list(FIELDS)},
                "empathy": {"type": "string"},
                "slot_id": {"type": "string"},
            },
            "required": ["intent"],
        },
    },
]

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
        if looks_spanish(raw):
            state.language = "es"
        local = classify_emergency(raw)
        remote = ("none", None)
        if self.model is not None and local[0] != "definite":
            remote = _claude_hazard(self.model, raw)
        level, label = _stricter(local, remote)
        if level == "definite" and label:
            state.hazard = label
        if state.hazard or wants_human(raw) or level in {"definite", "ask", "advice"}:
            return self.engine.handle(state, raw)
        if self.model is None:
            return self.engine.handle(state, raw)
        try:
            result = self._model_turn(state, raw)
        except Exception:
            result = self.engine.handle(state, raw)
        _remember(state, raw, result.say)
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
            return self._record(state, payload)
        if name == "find_slots":
            body, say = self._find_slots(state, str(payload.get("preference") or utterance))
            return body, say, None
        if name == "hold_slot":
            body, say = self._hold(state, str(payload.get("slot_id") or ""))
            return body, say, None
        if name == "book":
            refusal = self._refuse_slot(state, str(payload.get("slot_id") or state.selected or ""))
            if refusal:
                return refusal[0], refusal[1], None
            state.selected = str(payload.get("slot_id") or state.selected or "")
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
        empathy = payload.get("empathy")
        if payload.get("slot_id") and str(payload.get("slot_id")) in state.offered:
            state.selected = str(payload["slot_id"])
        facts = self._facts(state, utterance)
        spoken = render(intent, field if isinstance(field, str) else None, empathy if isinstance(empathy, str) else None, facts)
        if spoken is None:
            return {"ok": False, "speak_rejected": True, "error": "That line cannot be spoken."}, "", None
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

    def _record(self, state: SessionState, payload: dict) -> tuple[dict, str, None]:
        name = guess_bare_name(str(payload.get("name") or ""))
        phone, _blank = extract_phone(str(payload.get("phone") or ""))
        address_text = " ".join(
            part for part in (str(payload.get("address") or ""), str(payload.get("unit") or "")) if part
        )
        street = extract_street(address_text, self.engine.config.cities)
        unit = extract_unit(address_text)
        if street and unit and unit.lower() not in street.lower():
            street = f"{street} {unit}"
        found_zip = extract_zip(address_text)
        city = extract_city(address_text, self.engine.config.cities)
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
        if missing:
            field = {"name": "name", "phone": "phone", "address": "address"}[missing[0]]
            spoken = render("ask_field", field, None, {"language": state.language, "business": self.engine.config.name, "agent": self.engine.config.agent_name})
            return {"ok": False, "missing": missing, "say": spoken}, spoken or "", None
        spoken = _read_back(state)
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

    def _hold(self, state: SessionState, slot_id: str) -> tuple[dict, str]:
        refusal = self._refuse_slot(state, slot_id)
        if refusal:
            return {"ok": False, "error": refusal[0]["error"]}, refusal[1]
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


def _remember(state: SessionState, caller: str, reply: str) -> None:
    state.messages.append({"role": "user", "content": caller})
    state.messages.append({"role": "assistant", "content": reply})
    if len(state.messages) > 8:
        state.messages = state.messages[-8:]
