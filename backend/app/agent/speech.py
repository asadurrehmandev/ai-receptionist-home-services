"""Caller-facing speech is rendered here, from a fixed intent and tool facts.

The model may choose an intent and a short empathy line. It may not invent a
time, a price, a phone number, a promise, or a repair instruction. Anything
that fails the empathy check is dropped and the rules engine speaks instead.
"""

from __future__ import annotations

import re

INTENTS = (
    "greet",
    "ask_field",
    "offer_slots",
    "confirm_booking",
    "quote_standard_prices",
    "transfer",
    "cancel_flow",
    "goodbye",
    "small_talk",
)

FIELDS = ("issue", "name", "phone", "address", "time")

_BANNED = re.compile(
    r"\d|"
    r"\b(am|pm|noon|midnight|o'clock|oclock|half past|quarter|ish|"
    r"tomorrow|tonight|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"january|february|march|april|may|june|july|august|september|october|november|december|"
    r"dollar|dollars|bucks|percent|free|waive|waived|discount|comp|cheaper|"
    r"on the house|on the way|within the hour|"
    r"booked|scheduled|reserved|texted|paged|cancelled|canceled|rescheduled|"
    r"relight|yourself|diy|i sent|i've sent|i paged|direct line)\b",
    re.I,
)


def empathy_ok(text: str | None) -> bool:
    """A short human line with no facts, promises, or instructions."""
    raw = (text or "").strip()
    if not raw:
        return True
    if len(raw) > 120:
        return False
    if _BANNED.search(raw):
        return False
    return True


def render(intent: str, field: str | None, empathy: str | None, facts: dict) -> str | None:
    """Fill a template. Return None when the intent cannot be spoken safely."""
    if intent not in INTENTS:
        return None
    if not empathy_ok(empathy):
        return None
    body = _body(intent, field, facts)
    if body is None:
        return None
    prefix = (empathy or "").strip()
    if prefix:
        return f"{prefix} {body}"
    return body


def _body(intent: str, field: str | None, facts: dict) -> str | None:
    lang = facts.get("language") or "en"
    if intent == "greet":
        return _pick(
            lang,
            f"Thank you for calling {facts['business']}. I'm {facts['agent']}. What's going on?",
            f"Gracias por llamar a {facts['business']}. Soy {facts['agent']}. ¿Qué está pasando?",
        )
    if intent == "ask_field":
        return _ask(lang, field)
    if intent == "offer_slots":
        windows = facts.get("windows") or ""
        if not windows:
            return None
        return _pick(
            lang,
            f"I can come {windows}. Which of those works?",
            f"Puedo ir {windows}. ¿Cuál le queda?",
        )
    if intent == "confirm_booking":
        when = facts.get("when")
        where = facts.get("address")
        phone = facts.get("phone_display")
        if not when or not where:
            return None
        return _pick(
            lang,
            f"Should I lock that in for {when} at {where}? I'll note {phone} on the visit.",
            f"¿Lo dejo para {when} en {where}? Anoto {phone} en la visita.",
        )
    if intent == "quote_standard_prices":
        quote = facts.get("quote")
        if not quote:
            return None
        return quote
    if intent == "transfer":
        if not facts.get("transfer_allowed"):
            return None
        who = facts.get("on_call") or "the on-call technician"
        return _pick(
            lang,
            f"I'm connecting you to {who}. Please stay on the line. "
            "If you smell gas, leave the house and call 911 or your gas company.",
            f"Lo comunico con {who}. Quédese en la línea. "
            "Si huele a gas, salga de la casa y llame al 911 o a la compañía de gas.",
        )
    if intent == "cancel_flow":
        return _pick(
            lang,
            "I need the last four digits of the phone on the visit, and the day it is scheduled. "
            "I won't read the address before those match.",
            "Necesito los últimos cuatro dígitos del teléfono de la visita y el día. "
            "No leo la dirección antes de que coincidan.",
        )
    if intent == "goodbye":
        return _pick(lang, "Thanks for calling. Goodbye.", "Gracias por llamar. Adiós.")
    if intent == "small_talk":
        return _pick(
            lang,
            "I can help with a repair, an estimate, an existing visit, or an emergency.",
            "Puedo ayudar con una reparación, un estimado, una visita, o una emergencia.",
        )
    return None


def _ask(lang: str, field: str | None) -> str | None:
    prompts = {
        "issue": ("What seems to be the problem at the property?", "¿Qué problema hay en la propiedad?"),
        "name": ("Who am I speaking with? Can I get your first and last name?", "¿Con quién hablo? ¿Su nombre y apellido?"),
        "phone": ("What's the best phone number for the technician?", "¿Cuál es el mejor teléfono para el técnico?"),
        "address": ("What's the street address?", "¿Cuál es la dirección?"),
        "time": ("What day and time work for the visit?", "¿Qué día y hora le quedan para la visita?"),
    }
    pair = prompts.get(field or "")
    if pair is None:
        return None
    return _pick(lang, pair[0], pair[1])


def _pick(lang: str, english: str, spanish: str) -> str:
    if lang == "es":
        return spanish
    return english
