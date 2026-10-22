"""TwiML for Twilio voice webhooks, including request signature checks."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from uuid import uuid4
from xml.sax.saxutils import escape

from fastapi import Request

from app.config_loader import BusinessConfig
from app.settings import Settings


def twilio_signature(url: str, params: dict[str, str], token: str) -> str:
    material = url + "".join(f"{key}{params[key]}" for key in sorted(params))
    digest = hmac.new(token.encode("utf-8"), material.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8")


def signature_is_valid(url: str, params: dict[str, str], token: str, provided: str | None) -> bool:
    if not token:
        return True
    if not provided:
        return False
    expected = twilio_signature(url, params, token)
    return hmac.compare_digest(expected, provided)


def public_url(request: Request, settings: Settings) -> str:
    query = request.url.query
    path = request.url.path + (("?" + query) if query else "")
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/") + path
    return str(request.url)


def mint_stream_token(secret: str, ttl: int = 120) -> str:
    """Short-lived HMAC for a Media Stream URL. This is not the admin token."""
    expires = int(time.time()) + ttl
    nonce = uuid4().hex
    message = f"{nonce}.{expires}".encode()
    signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()[:32]
    return f"{nonce}.{expires}.{signature}"


def stream_token_valid(secret: str, token: str) -> bool:
    if not secret or not token:
        return False
    try:
        nonce, expires, signature = token.split(".", 2)
        if int(expires) < time.time():
            return False
    except ValueError:
        return False
    message = f"{nonce}.{expires}".encode()
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()[:32]
    return hmac.compare_digest(expected, signature)


def stream_secret(settings: Settings) -> str:
    return settings.admin_token or settings.twilio_auth_token or ""


def stream_ws_url(request: Request, settings: Settings) -> str:
    if settings.public_base_url:
        base = settings.public_base_url.rstrip("/")
    else:
        base = str(request.base_url).rstrip("/")
    if base.startswith("https://"):
        base = "wss://" + base[len("https://") :]
    elif base.startswith("http://"):
        base = "ws://" + base[len("http://") :]
    url = base + "/api/voice/stream"
    secret = stream_secret(settings)
    if secret:
        url += "?token=" + mint_stream_token(secret)
    return url


def gather_twiml(say: str, action: str, voice: str, language: str = "en-US") -> str:
    spoken = escape(say)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Gather input="speech" action="{escape(action)}" method="POST" speechTimeout="auto" '
        f'timeout="5" actionOnEmptyResult="true" language="{escape(language)}">'
        f'<Say voice="{escape(voice)}">{spoken}</Say>'
        "</Gather>"
        f'<Say voice="{escape(voice)}">I did not catch that. Please call again.</Say>'
        "<Hangup/>"
        "</Response>"
    )


def say_and_hangup(say: str, voice: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Say voice="{escape(voice)}">{escape(say)}</Say>'
        "<Hangup/>"
        "</Response>"
    )


def dial_twiml(say: str, number: str, voice: str, action: str, caller_id: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Say voice="{escape(voice)}">{escape(say)}</Say>'
        f'<Dial timeout="20" action="{escape(action)}" callerId="{escape(caller_id)}">'
        f"<Number>{escape(number)}</Number>"
        "</Dial>"
        "</Response>"
    )


def stream_twiml(url: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response><Connect>"
        f'<Stream url="{escape(url)}"/>'
        "</Connect></Response>"
    )


def use_media_stream(config: BusinessConfig, settings: Settings) -> bool:
    if config.voice_mode == "gather":
        return False
    if not settings.media_stream_ready:
        return False
    return config.voice_mode in {"auto", "stream"}
