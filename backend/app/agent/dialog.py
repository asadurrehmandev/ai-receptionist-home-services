"""Claude tool-calling dialog. The rules engine remains the no-key fallback.

Tools own bookings, cancellations, lookups, and transfers. A deterministic
emergency pre-filter can force a transfer before the model speaks. Any clock
time or price in the model's own words must appear in a tool result from this
turn; otherwise the tool sentence (or the rule sentence) is what the caller hears.
"""

from __future__ import annotations

import json
from uuid import uuid4

from app.agent.engine import Engine, SessionState, TurnResult
from app.agent.facts import speech_supported
from app.agent.nlu import classify_emergency, wants_human

TOOL_SPECS = [
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
        "description": "Hold one slot id returned by find_slots so nobody else is offered it.",
        "input_schema": {
            "type": "object",
            "properties": {"slot_id": {"type": "string"}},
            "required": ["slot_id"],
        },
    },
    {
        "name": "book",
        "description": "Book the held slot. Uses the name, phone, and address already stored for this call.",
        "input_schema": {
            "type": "object",
            "properties": {"slot_id": {"type": "string"}},
            "required": ["slot_id"],
        },
    },
    {
        "name": "lookup_booking",
        "description": "Find an existing booking by phone number. A first name is not accepted.",
        "input_schema": {
            "type": "object",
            "properties": {"phone": {"type": "string"}},
            "required": ["phone"],
        },
    },
    {
        "name": "cancel",
        "description": "Cancel a booking. confirmed must be true, and only after the caller agreed to the readback.",
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
        "description": "Transfer the live call to the on-call technician.",
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
            "required": ["reason"],
        },
    },
]


class Dialog:
    def __init__(self, engine: Engine, model) -> None:
        self.engine = engine
        self.model = model

    def handle(self, state: SessionState, text: str) -> TurnResult:
        level, _label = classify_emergency(text or "")
        if level == "definite" or wants_human(text or ""):
            result = self.engine.handle(state, text)
            result.say = _guard_emergency(result.say)
            return result
        if self.model is None:
            return self.engine.handle(state, text)
        try:
            return self._model_turn(state, text)
        except Exception:
            return self.engine.handle(state, text)

    def _model_turn(self, state: SessionState, text: str) -> TurnResult:
        summary = {
            "phase": state.phase,
            "name": state.name,
            "phone": state.phone,
            "address": state.address,
            "issue": state.issue,
            "selected": state.selected,
            "booking_id": state.booking_id,
            "outcome": state.outcome,
        }
        messages = list(state.events and [] or [])
        messages = [
            {
                "role": "user",
                "content": "STATE " + json.dumps(summary) + "\nCALLER (untrusted): " + json.dumps(text),
            }
        ]
        allowed: list[str] = []
        tool_say = ""
        emergency = False
        executed = False
        for _ in range(4):
            response = self.model.complete(messages, TOOL_SPECS)
            content = response.get("content") or []
            messages.append({"role": "assistant", "content": content})
            tool_uses = [block for block in content if block.get("type") == "tool_use"]
            texts = [block.get("text") or "" for block in content if block.get("type") == "text"]
            if any(block.get("name") == "follow_rules" for block in tool_uses):
                return self.engine.handle(state, text)
            if not tool_uses:
                spoken = " ".join(texts).strip()
                if spoken and speech_supported(spoken, "\n".join(allowed), emergency=emergency):
                    return TurnResult(say=spoken, events=[], latency_ms=0.0)
                if tool_say:
                    return TurnResult(say=tool_say, events=[], latency_ms=0.0)
                return self.engine.handle(state, text)
            results = []
            for call in tool_uses:
                payload, spoken, events, is_emergency = self._execute(state, call.get("name"), call.get("input") or {})
                executed = True
                emergency = emergency or is_emergency
                allowed.append(json.dumps(payload))
                if spoken:
                    tool_say = spoken
                    allowed.append(spoken)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call.get("id") or uuid4().hex,
                        "content": json.dumps(payload),
                    }
                )
            messages.append({"role": "user", "content": results})
            if tool_say and state.outcome in {"booked", "rescheduled", "cancelled", "escalated"}:
                break
        if tool_say and speech_supported(tool_say, tool_say, emergency=emergency):
            return TurnResult(say=tool_say, events=list(state.events[-4:]), latency_ms=0.0)
        if not executed:
            return self.engine.handle(state, text)
        return TurnResult(say=tool_say or "One moment.", events=[], latency_ms=0.0)

    def _execute(self, state: SessionState, name: str, payload: dict) -> tuple[dict, str, list, bool]:
        if name == "find_slots":
            result = self.engine.handle(state, str(payload.get("preference") or "the earliest you have"))
            return {"say": result.say, "offered": list(state.offered)}, result.say, result.events, False
        if name == "hold_slot":
            slot_id = str(payload.get("slot_id") or "")
            if slot_id:
                state.selected = slot_id
                state.phase = "confirm"
            result = self.engine._confirm_line(state, self.engine._selected(state)) if state.selected else "Which window?"
            return {"slot_id": state.selected, "say": result}, result, [], False
        if name == "book":
            if payload.get("slot_id"):
                state.selected = str(payload["slot_id"])
            result = self.engine._book(state, 0.0, reschedule=state.intent == "existing_booking" and bool(state.booking_id))
            return {"say": result.say, "booking_id": state.booking_id}, result.say, result.events, False
        if name == "lookup_booking":
            state.phone = str(payload.get("phone") or state.phone or "")
            result = self.engine._existing(state, "existing appointment", 0.0)
            return {"say": result.say}, result.say, result.events, False
        if name == "cancel":
            if not payload.get("confirmed"):
                return {"error": "confirmed must be true"}, "I need a clear yes before I cancel that visit.", [], False
            state.booking_id = str(payload.get("booking_id") or state.booking_id or "")
            result = self.engine._cancel_booking(state, 0.0)
            return {"say": result.say}, result.say, result.events, False
        if name == "transfer":
            reason = str(payload.get("reason") or "Caller requested a person")
            result = self.engine._escalate(state, 0.0, reason)
            return {"say": result.say, "to": self.engine.config.on_call_phone}, _guard_emergency(result.say), result.events, True
        return {"error": "unknown tool"}, "", [], False


def _guard_emergency(say: str) -> str:
    if speech_supported(say, say, emergency=True):
        return say
    return say
