"""Deepgram, ElevenLabs, and CRM webhook calls.

Claude lives in app.llm. The free-form rephrase step is gone: a model may
choose tools, and tool results are the only source of times and prices.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time

import httpx


class MissingKey(RuntimeError):
    pass


def sign_payload(payload: dict, secret: str) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def transcribe_mulaw(audio: bytes, api_key: str, client: httpx.Client | None = None) -> str:
    if not api_key:
        raise MissingKey("DEEPGRAM_API_KEY")
    own = client is None
    client = client or httpx.Client(timeout=20)
    try:
        response = client.post(
            "https://api.deepgram.com/v1/listen",
            params={"encoding": "mulaw", "sample_rate": "8000", "model": "nova-2"},
            headers={"Authorization": f"Token {api_key}"},
            content=audio,
        )
        response.raise_for_status()
        return response.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
    finally:
        if own:
            client.close()


def synthesize_ulaw(text: str, api_key: str, voice_id: str, client: httpx.Client | None = None) -> bytes:
    if not api_key:
        raise MissingKey("ELEVENLABS_API_KEY")
    own = client is None
    client = client or httpx.Client(timeout=30)
    try:
        response = client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            params={"output_format": "ulaw_8000"},
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_turbo_v2_5"},
        )
        response.raise_for_status()
        return response.content
    finally:
        if own:
            client.close()


def deliver_webhook(url: str, payload: dict, secret: str | None = None) -> dict:
    body = dict(payload)
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-Receptionist-Signature"] = sign_payload(body, secret)
    if not url:
        return {
            "status": "mock",
            "code": None,
            "detail": "Logged locally. Set crm.webhook_url to deliver to your CRM (GoHighLevel, HubSpot, or Zapier).",
        }
    delay = 0.05
    last = {"status": "error", "code": None, "detail": "not sent"}
    for _attempt in range(3):
        try:
            response = httpx.post(url, json=body, headers=headers, timeout=5)
        except httpx.HTTPError as exc:
            last = {"status": "error", "code": None, "detail": str(exc)}
            time.sleep(delay)
            delay *= 2
            continue
        status = "delivered" if response.status_code < 300 else "error"
        last = {"status": status, "code": response.status_code, "detail": response.text[:280]}
        if status == "delivered":
            return last
        time.sleep(delay)
        delay *= 2
    return last


def enqueue_webhook(url: str, payload: dict, secret: str | None, on_done) -> dict:
    """Deliver off the request path when a URL is set. Local logs stay synchronous."""
    if not url:
        result = deliver_webhook(url, payload, secret)
        on_done(result)
        return result

    def work() -> None:
        on_done(deliver_webhook(url, payload, secret))

    threading.Thread(target=work, daemon=True).start()
    return {"status": "queued", "code": None, "detail": "Delivery is running in the background."}


def send_sms(settings, to: str, body: str) -> dict:
    """Send a Twilio SMS only when a from-number is configured. Otherwise nothing is sent."""
    sid = getattr(settings, "twilio_account_sid", None)
    token = getattr(settings, "twilio_auth_token", None)
    sender = getattr(settings, "twilio_from_number", None)
    if not (sid and token and sender and to):
        return {"status": "not_sent", "detail": "No messaging number is configured."}
    try:
        response = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            data={"To": to, "From": sender, "Body": body},
            auth=(sid, token),
            timeout=5,
        )
    except httpx.HTTPError as exc:
        return {"status": "not_sent", "detail": str(exc)}
    if response.status_code < 300:
        return {"status": "sent", "detail": "Twilio accepted the message."}
    return {"status": "not_sent", "detail": response.text[:200]}
