"""Twilio Media Streams bridge.

With Deepgram and ElevenLabs keys, caller audio is turned into a reply while
the socket is still open. Silence after speech flushes a turn. The buffer is
capped. An emergency asks a CallUpdater to rewrite the live call with <Dial>
when Twilio account credentials exist. Gather remains the path that dials
without that extra credential.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable

from app.integrations import synthesize_ulaw, transcribe_mulaw

MAX_AUDIO_BYTES = 8000 * 20
SILENCE_BYTES = int(8000 * 0.4)
SILENCE = {0xFF, 0x7F}


class MediaBridge:
    def __init__(
        self,
        service,
        synthesize: Callable[[str], bytes] | None = None,
        transcribe: Callable[[bytes], str] | None = None,
        updater: Callable[[str, str], None] | None = None,
        dial_twiml: Callable[[str], str] | None = None,
        gather_url: str | None = None,
        on_call_phone: str | None = None,
        caller_id: str | None = None,
        dial_action: str | None = None,
    ) -> None:
        self.service = service
        self.synthesize = synthesize
        self.transcribe = transcribe
        self.updater = updater
        self.dial_twiml = dial_twiml
        self.gather_url = gather_url or "/api/voice/twilio/gather"
        self.on_call_phone = on_call_phone
        self.caller_id = caller_id
        self.dial_action = dial_action
        self.stream_sid: str | None = None
        self.call_sid: str | None = None
        self.call_id: str | None = None
        self.audio = bytearray()
        self.heard_speech = False
        self.pending_dial: str | None = None

    def handle(self, message: dict) -> list[dict]:
        event = message.get("event")
        if event == "connected":
            return []
        if event == "start":
            start = message.get("start") or {}
            self.stream_sid = start.get("streamSid")
            self.call_sid = start.get("callSid")
            started = self.service.start("twilio-stream", external_id=self.call_sid)
            self.call_id = started["id"]
            return self._speak(started["say"], outcome=None)
        if event == "media":
            payload = (message.get("media") or {}).get("payload") or ""
            if not payload:
                return []
            chunk = base64.b64decode(payload)
            frames: list[dict] = []
            if len(self.audio) + len(chunk) > MAX_AUDIO_BYTES:
                frames.extend(self._flush())
            self.audio.extend(chunk[: MAX_AUDIO_BYTES - len(self.audio)])
            if any(byte not in SILENCE for byte in chunk):
                self.heard_speech = True
            if self.heard_speech and self._trailing_silence() >= SILENCE_BYTES:
                frames.extend(self._flush())
            return frames
        if event == "stop":
            if self.audio and self.transcribe is not None:
                return self._flush()
            if self.transcribe is None:
                return [self._mark("stt-unconfigured")]
            return [self._mark("empty-transcript")]
        return []

    def apply_transcript(self, text: str) -> list[dict]:
        if self.call_id is None:
            started = self.service.start("twilio-stream", external_id=self.call_sid)
            self.call_id = started["id"]
        result = self.service.turn(self.call_id, text)
        frames = self._speak(result["say"], outcome=result.get("outcome"))
        if result.get("outcome") == "escalated":
            frames.append(self._mark("transfer"))
            twiml = self.dial_twiml(result["say"]) if self.dial_twiml else None
            self.pending_dial = twiml
            if twiml and self.updater and self.call_sid:
                self.updater(self.call_sid, twiml)
        return frames

    def _flush(self) -> list[dict]:
        audio = bytes(self.audio)
        self.audio = bytearray()
        self.heard_speech = False
        if self.transcribe is None or not audio:
            return []
        try:
            transcript = self.transcribe(audio)
        except Exception:
            frames = [self._mark("stt-failed")]
            if not self._rest_fallback("I didn't catch that. Please tell me again what's going on.", outcome=None):
                frames.append(self._mark("say-fallback"))
            return frames
        if not transcript:
            return [self._mark("empty-transcript")]
        return self.apply_transcript(transcript)

    def _trailing_silence(self) -> int:
        count = 0
        for byte in reversed(self.audio):
            if byte not in SILENCE:
                break
            count += 1
        return count

    def _fallback_twiml(self, text: str, outcome: str | None) -> str:
        from app.voice.twilio import dial_twiml, say_and_continue

        voice = "Polly.Joanna"
        if outcome == "escalated" and self.on_call_phone and self.dial_action and self.caller_id:
            return dial_twiml(text, self.on_call_phone, voice, self.dial_action, self.caller_id)
        return say_and_continue(text, voice, self.gather_url)

    def _rest_fallback(self, text: str, outcome: str | None) -> bool:
        if not (self.updater and self.call_sid):
            return False
        try:
            self.updater(self.call_sid, self._fallback_twiml(text, outcome))
        except Exception:
            return False
        return True

    def _speak(self, text: str, outcome: str | None = None) -> list[dict]:
        frames: list[dict] = []
        if self.synthesize is None:
            frames.append(self._mark("tts-unconfigured"))
            frames.append(self._mark("reply"))
            return frames
        try:
            audio = self.synthesize(text)
        except Exception:
            frames.append(self._mark("tts-failed"))
            if not self._rest_fallback(text, outcome):
                frames.append(self._mark("say-fallback"))
            return frames
        frames.append({"event": "clear", "streamSid": self.stream_sid})
        for offset in range(0, len(audio), 160):
            chunk = audio[offset : offset + 160]
            frames.append(
                {
                    "event": "media",
                    "streamSid": self.stream_sid,
                    "media": {"payload": base64.b64encode(chunk).decode("ascii")},
                }
            )
        frames.append(self._mark("reply"))
        return frames

    def _mark(self, name: str) -> dict:
        return {"event": "mark", "streamSid": self.stream_sid, "mark": {"name": name}}


def bridge_from_settings(service, settings) -> MediaBridge:
    synthesize = None
    transcribe = None
    updater = None
    if settings.elevenlabs_api_key:
        voice = settings.elevenlabs_voice_id

        def synthesize(text: str, voice=voice, key=settings.elevenlabs_api_key) -> bytes:
            return synthesize_ulaw(text, key, voice)

    if settings.deepgram_api_key:

        def transcribe(audio: bytes, key=settings.deepgram_api_key) -> str:
            return transcribe_mulaw(audio, key)

    if settings.twilio_account_sid and settings.twilio_auth_token:

        def updater(call_sid: str, twiml: str, sid=settings.twilio_account_sid, token=settings.twilio_auth_token) -> None:
            import httpx

            httpx.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls/{call_sid}.json",
                data={"Twiml": twiml},
                auth=(sid, token),
                timeout=5,
            )

    base = (settings.public_base_url or "").rstrip("/")
    gather_url = f"{base}/api/voice/twilio/gather" if base else "/api/voice/twilio/gather"
    dial_action = f"{base}/api/voice/twilio/dial-status" if base else "/api/voice/twilio/dial-status"
    return MediaBridge(
        service,
        synthesize=synthesize,
        transcribe=transcribe,
        updater=updater,
        gather_url=gather_url,
        on_call_phone=service.config.on_call_phone,
        caller_id=service.config.phone_e164,
        dial_action=dial_action,
    )


def loads_message(raw: str) -> dict:
    message = json.loads(raw)
    if not isinstance(message, dict):
        raise ValueError("Twilio media message must be an object")
    return message
