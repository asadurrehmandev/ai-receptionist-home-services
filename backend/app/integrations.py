"""Optional LLM, Deepgram, ElevenLabs, and CRM webhook calls.

Every function no-ops or raises MissingKey when the matching secret is absent.
The rule engine remains the source of truth for bookings and transfers.
"""

from __future__ import annotations

import re

import httpx

from app.agent.engine import SessionState

TIME_TOKEN = re.compile(r"\d{1,2}:\d{2}\s*[AP]M", re.I)
MONEY_TOKEN = re.compile(r"\$\d[\d,]*")


class MissingKey(RuntimeError):
    pass


def rephrase(say: str, state: SessionState, user_text: str, settings) -> str:
    """Rewrite the spoken line when an OpenAI-compatible key is set.

    The rewrite is discarded if it drops a time or a price the rules included.
    """
    if not settings.openai_api_key:
        return say
    system = (
        "You are Riley, a calm phone receptionist for a home-service company. "
        "Rewrite the draft reply so it sounds natural spoken aloud. "
        "Keep every clock time, dollar amount, address, phone number, and name exactly as written. "
        "Do not add new offers. Reply with the spoken sentence only."
    )
    user = (
        f"Caller just said: {user_text}\n"
        f"Intent: {state.intent}. Phase: {state.phase}. Outcome: {state.outcome}.\n"
        f"Draft reply: {say}"
    )
    try:
        response = httpx.post(
            settings.openai_base_url.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "temperature": 0.3,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=12,
        )
        response.raise_for_status()
        rewritten = response.json()["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError, TypeError):
        return say
    if not rewritten:
        return say
    if not _preserves(say, rewritten):
        return say
    return rewritten


def _preserves(draft: str, rewritten: str) -> bool:
    for token in TIME_TOKEN.findall(draft):
        if token.lower() not in rewritten.lower():
            return False
    for token in MONEY_TOKEN.findall(draft):
        if token not in rewritten:
            return False
    return True


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


def deliver_webhook(url: str, payload: dict) -> dict:
    if not url:
        return {"status": "mock", "code": None, "detail": "Logged locally. Set crm.webhook_url to deliver to your CRM (GoHighLevel, HubSpot, or Zapier)."}
    try:
        response = httpx.post(url, json=payload, timeout=5)
    except httpx.HTTPError as exc:
        return {"status": "error", "code": None, "detail": str(exc)}
    status = "delivered" if response.status_code < 300 else "error"
    return {"status": status, "code": response.status_code, "detail": response.text[:280]}
