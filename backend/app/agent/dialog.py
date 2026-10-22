"""Claude tool-calling dialog. The rules engine remains the no-key fallback.

Tools own bookings, cancellations, lookups, and transfers. A hazard anywhere
in the call forces a transfer before the model speaks. Clock times, prices,
discounts, and booking claims in the model's own words have to appear in a
tool result from this turn. The model cannot confirm a cancel or invent a slot.
"""

from __future__ import annotations

import json
from time import monotonic, perf_counter
from uuid import uuid4

from app.agent.engine import Engine, SessionState, TurnResult
from app.agent.facts import speech_supported
from app.agent.nlu import classify_emergency, is_clean_yes, wants_human
from app.agent.scheduling import available_slots, format_slot, join_slots, parse_preference

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
        "description": "Hold one slot id that find_slots returned on this call. Requires the caller's name, phone, and service-area address.",
        "input_schema": {
            "type": "object",
            "properties": {"slot_id": {"type": "string"}},
            "required": ["slot_id"],
        },
    },
    {
        "name": "book",
        "description": "Book a slot id that find_slots returned. Requires name, a 10-digit phone, and an in-area address. Refuses if those are missing.",
        "input_schema": {
            "type": "object",
            "properties": {"slot_id": {"type": "string"}},
            "required": ["slot_id"],
        },
    },
    {
        "name": "lookup_booking",
        "description": "Look up a visit from the last four digits and the day the caller just spoke. A booking id is ignored.",
        "input_schema": {
            "type": "object",
            "properties": {"phone": {"type": "string"}},
            "required": ["phone"],
        },
    },
    {
        "name": "cancel",
        "description": "Cancel only after lookup verified the caller and their latest words are a clear yes. The booking id and confirmed flag are ignored.",
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

TURN_BUDGET_S = 8.0
CALL_TIMEOUT_S = 5.0
MAX_ROUNDS = 2


class Dialog:
    def __init__(self, engine: Engine, model) -> None:
        self.engine = engine
        self.model = model

    def handle(self, state: SessionState, text: str) -> TurnResult:
        level, label = classify_emergency(text or "")
        if level == "definite" and label:
            state.hazard = label
        if state.hazard or wants_human(text or ""):
            result = self.engine.handle(state, text)
            if state.hazard or result.say:
                result.say = _transfer_script(self.engine, state, result.say)
            return result
        if level == "advice" or self.model is None:
            return self.engine.handle(state, text)
        try:
            result = self._model_turn(state, text)
        except Exception:
            result = self.engine.handle(state, text)
        _remember(state, text, result.say)
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
            "hazard": state.hazard,
        }
        messages = list(state.messages)[-6:]
        messages.append(
            {
                "role": "user",
                "content": "STATE " + json.dumps(summary) + "\nCALLER (untrusted): " + json.dumps(text),
            }
        )
        allowed: list[str] = []
        tool_say = ""
        booked_ok = False
        for _ in range(MAX_ROUNDS):
            remaining = deadline - monotonic()
            if remaining <= 0.3:
                break
            timeout = min(CALL_TIMEOUT_S, remaining)
            response = self.model.complete(messages, TOOL_SPECS, timeout=timeout)
            content = response.get("content") or []
            messages.append({"role": "assistant", "content": content})
            tool_uses = [block for block in content if block.get("type") == "tool_use"]
            texts = [block.get("text") or "" for block in content if block.get("type") == "text"]
            if any(block.get("name") == "follow_rules" for block in tool_uses):
                return self.engine.handle(state, text)
            if not tool_uses:
                spoken = " ".join(texts).strip()
                if state.hazard:
                    return self.engine._escalate(state, perf_counter(), state.hazard)
                if spoken and speech_supported(spoken, "\n".join(allowed), booked_ok=booked_ok):
                    return TurnResult(say=spoken, events=[], latency_ms=0.0)
                if tool_say and speech_supported(tool_say, "\n".join(allowed), booked_ok=booked_ok):
                    return TurnResult(say=tool_say, events=list(state.events[-4:]), latency_ms=0.0)
                return self.engine.handle(state, text)
            results = []
            for call in tool_uses:
                payload, spoken, is_emergency = self._execute(state, text, call.get("name"), call.get("input") or {})
                if is_emergency:
                    state.hazard = state.hazard or str(payload.get("reason") or "transfer")
                booked_ok = booked_ok or bool(payload.get("booked"))
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
            if state.hazard:
                return self.engine._escalate(state, perf_counter(), state.hazard)
            if tool_say and state.outcome in {"booked", "rescheduled", "cancelled", "escalated"}:
                break
        if state.hazard:
            return self.engine._escalate(state, perf_counter(), state.hazard)
        if tool_say and speech_supported(tool_say, "\n".join(allowed), booked_ok=booked_ok):
            return TurnResult(say=tool_say, events=list(state.events[-4:]), latency_ms=0.0)
        return self.engine.handle(state, text)

    def _execute(self, state: SessionState, utterance: str, name: str, payload: dict) -> tuple[dict, str, bool]:
        if state.hazard or classify_emergency(utterance)[0] == "definite":
            result = self.engine._escalate(state, perf_counter(), state.hazard or "Hazard")
            return {"say": result.say, "reason": state.hazard}, result.say, True
        if name == "find_slots":
            return self._find_slots(state, str(payload.get("preference") or utterance))
        if name == "hold_slot":
            return self._hold(state, str(payload.get("slot_id") or ""))
        if name == "book":
            return self._book(state, str(payload.get("slot_id") or state.selected or ""))
        if name == "lookup_booking":
            result = self.engine._existing(state, utterance, perf_counter())
            return {"say": result.say, "verified": state.verified}, result.say, False
        if name == "cancel":
            if not state.verified or not state.booking_id or not is_clean_yes(utterance):
                return (
                    {"ok": False, "error": "Cancel needs a verified visit and a clear yes from the caller."},
                    "I need the last four digits, the visit day, and a clear yes before I cancel anything.",
                    False,
                )
            result = self.engine._cancel_booking(state, perf_counter())
            return {"ok": True, "say": result.say}, result.say, False
        if name == "transfer":
            reason = str(payload.get("reason") or "Caller requested a person")
            result = self.engine._escalate(state, perf_counter(), reason)
            return {"say": result.say, "reason": reason}, result.say, True
        return {"error": "unknown tool"}, "", False

    def _find_slots(self, state: SessionState, preference_text: str) -> tuple[dict, str, bool]:
        preference = parse_preference(preference_text, self.engine.now)
        slots, _relaxed = available_slots(
            self.engine.config,
            self.engine.now,
            self.engine.calendar.busy(),
            preference=preference,
            limit=3,
        )
        state.offered = [slot.isoformat() for slot in slots]
        if not slots:
            say = "I don't have an open window in that range."
        else:
            say = f"I can come {join_slots(slots)}. Which of those works?"
        payload = {"slots": [{"id": slot.isoformat(), "label": format_slot(slot)} for slot in slots], "say": say}
        return payload, say, False

    def _hold(self, state: SessionState, slot_id: str) -> tuple[dict, str, bool]:
        refusal = self._refuse_slot(state, slot_id)
        if refusal:
            return refusal
        state.selected = slot_id
        state.phase = "confirm"
        moment = self.engine._selected(state)
        say = self.engine._confirm_line(state, moment) if moment else "Which window?"
        return {"ok": True, "slot_id": slot_id, "say": say}, say, False

    def _book(self, state: SessionState, slot_id: str) -> tuple[dict, str, bool]:
        refusal = self._refuse_slot(state, slot_id)
        if refusal:
            return refusal
        state.selected = slot_id
        result = self.engine._book(state, perf_counter(), reschedule=bool(state.verified and state.pending_action == "reschedule"))
        booked = state.outcome in {"booked", "rescheduled"}
        return {"ok": booked, "booked": booked, "say": result.say, "booking_id": state.booking_id}, result.say, False

    def _refuse_slot(self, state: SessionState, slot_id: str) -> tuple[dict, str, bool] | None:
        if slot_id not in state.offered:
            return {"ok": False, "error": "That slot was not offered by find_slots."}, "That window is not one I offered.", False
        if not _customer_ready(self.engine, state):
            return (
                {"ok": False, "error": "Name, phone, and an in-area address are required."},
                "I still need the name, a 10-digit phone, and a service-area address before I hold a window.",
                False,
            )
        return None


def _customer_ready(engine: Engine, state: SessionState) -> bool:
    digits = "".join(char for char in (state.phone or "") if char.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if not state.name or len(digits) != 10 or not state.address:
        return False
    return engine._area(state) == "ok"


def _transfer_script(engine: Engine, state: SessionState, say: str) -> str:
    if state.language == "es":
        return (
            f"Esto es urgente. Lo comunico con {engine.config.on_call_name}. "
            "Si huele a gas, salga de la casa y llame al 911."
        )
    if "911" in say or "on-call" in say.lower() or "connecting" in say.lower():
        return say
    return (
        f"I'm treating this as an emergency and connecting you to {engine.config.on_call_name}. "
        "If you smell gas, leave the house and call 911."
    )


def _remember(state: SessionState, caller: str, reply: str) -> None:
    state.messages.append({"role": "user", "content": caller})
    state.messages.append({"role": "assistant", "content": reply})
    if len(state.messages) > 8:
        state.messages = state.messages[-8:]
