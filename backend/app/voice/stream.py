"""Twilio Media Streams bridge.

Audio is transcribed with Deepgram and spoken with ElevenLabs ulaw 8 kHz
when those keys exist. Without them the socket still accepts Twilio's
protocol and marks the stream as waiting on STT/TTS configuration.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable

from app.integrations import synthesize_ulaw, transcribe_mulaw


class MediaBridge:
    def __init__(
        self,
        service,
        synthesize: Callable[[str], bytes] | None = None,
        transcribe: Callable[[bytes], str] | None = None,
    ) -> None:
        self.service = service
        self.synthesize = synthesize
        self.transcribe = transcribe
        self.stream_sid: str | None = None
        self.call_id: str | None = None
        self.audio = bytearray()

    def handle(self, message: dict) -> list[dict]:
        event = message.get("event")
        if event == "connected":
            return []
        if event == "start":
            start = message.get("start") or {}
            self.stream_sid = start.get("streamSid")
            call_sid = start.get("callSid")
            started = self.service.start("twilio-stream", external_id=call_sid)
            self.call_id = started["id"]
            return self._speak(started["say"])
        if event == "media":
            payload = (message.get("media") or {}).get("payload") or ""
            if payload:
                self.audio.extend(base64.b64decode(payload))
            return []
        if event == "stop":
            if self.transcribe is None:
                return [self._mark("stt-unconfigured")]
            transcript = self.transcribe(bytes(self.audio))
            if not transcript:
                return [self._mark("empty-transcript")]
            return self.apply_transcript(transcript)
        return []

    def apply_transcript(self, text: str) -> list[dict]:
        if self.call_id is None:
            started = self.service.start("twilio-stream")
            self.call_id = started["id"]
        result = self.service.turn(self.call_id, text)
        frames = self._speak(result["say"])
        if result.get("outcome") == "escalated":
            frames.append(self._mark("transfer"))
        return frames

    def _speak(self, text: str) -> list[dict]:
        frames: list[dict] = []
        if self.synthesize is None:
            frames.append(self._mark("tts-unconfigured"))
            frames.append(self._mark("reply"))
            return frames
        audio = self.synthesize(text)
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
    if settings.elevenlabs_api_key:
        voice = settings.elevenlabs_voice_id

        def synthesize(text: str, voice=voice, key=settings.elevenlabs_api_key) -> bytes:
            return synthesize_ulaw(text, key, voice)

    if settings.deepgram_api_key:

        def transcribe(audio: bytes, key=settings.deepgram_api_key) -> str:
            return transcribe_mulaw(audio, key)

    return MediaBridge(service, synthesize=synthesize, transcribe=transcribe)


def loads_message(raw: str) -> dict:
    message = json.loads(raw)
    if not isinstance(message, dict):
        raise ValueError("Twilio media message must be an object")
    return message
