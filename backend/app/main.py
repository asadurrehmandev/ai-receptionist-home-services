"""HTTP surface: browser demo, dispatch APIs, and Twilio voice."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app.config_loader import load_business
from app.integrations import deliver_webhook
from app.seed import seed_demo
from app.service import ReceptionService
from app.settings import Settings, settings_from_env
from app.store import Store
from app.voice.stream import bridge_from_settings, loads_message
from app.voice.twilio import (
    dial_twiml,
    gather_twiml,
    public_url,
    say_and_hangup,
    signature_is_valid,
    stream_twiml,
    stream_ws_url,
    use_media_stream,
)


class TurnIn(BaseModel):
    text: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or settings_from_env()
    config = load_business(settings.config_path)
    store = Store(settings.db_path)
    service = ReceptionService(config, store, settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if settings.seed_on_start and store.count_calls() == 0:
            seed_demo(service)
        yield
        store.close()

    app = FastAPI(title="AI Receptionist for Home Services", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.config = config
    app.state.store = store
    app.state.service = service

    @app.get("/api/health")
    def health():
        return {
            "ok": True,
            "business": config.name,
            "llm": bool(settings.openai_api_key),
            "stt": bool(settings.deepgram_api_key),
            "tts": bool(settings.elevenlabs_api_key),
            "twilio_signature": bool(settings.twilio_auth_token),
            "media_stream_ready": settings.media_stream_ready,
            "brain": "rules+llm" if settings.openai_api_key else "rules",
        }

    @app.get("/api/config")
    def get_config():
        payload = config.public_dict()
        payload["runtime"] = health()
        return payload

    @app.get("/api/metrics")
    def metrics():
        return store.metrics()

    @app.get("/api/overview")
    def overview():
        calls = store.list_calls()
        metrics_payload = store.metrics()
        now = datetime.now(config.zone)
        upcoming = []
        for booking in store.list_bookings():
            if booking["status"] != "booked":
                continue
            start = datetime.fromisoformat(booking["start"])
            if start >= now - timedelta(hours=3):
                upcoming.append(booking)
        webhooks = store.list_events("webhook")
        return {
            "business": config.public_dict()["business"],
            "on_call": {"name": config.on_call_name, "phone": config.on_call_phone},
            "counts": metrics_payload["outcomes"],
            "total_calls": len(calls),
            "metrics": metrics_payload,
            "recent_calls": calls[:8],
            "upcoming": upcoming[:6],
            "leads": store.list_leads()[:6],
            "webhooks": webhooks[:6],
        }

    @app.get("/api/calls")
    def list_calls():
        return {"calls": store.list_calls()}

    @app.get("/api/calls/{call_id}")
    def get_call(call_id: str):
        call = store.get_call(call_id)
        if call is None:
            raise HTTPException(status_code=404, detail="Call not found")
        return call

    @app.get("/api/bookings")
    def list_bookings():
        return {"bookings": store.list_bookings()}

    @app.get("/api/leads")
    def list_leads():
        return {"leads": store.list_leads()}

    @app.get("/api/events")
    def list_events(type: str | None = None):
        return {"events": store.list_events(type)}

    @app.post("/api/events/{event_id}/replay")
    def replay_event(event_id: int):
        match = next((event for event in store.list_events() if event["id"] == event_id), None)
        if match is None or match["type"] != "webhook":
            raise HTTPException(status_code=404, detail="Webhook event not found")
        body = {key: value for key, value in match["payload"].items() if key != "delivery"}
        return deliver_webhook(config.webhook_url, body)

    @app.post("/api/demo/calls")
    def start_demo():
        return service.start("simulator")

    @app.post("/api/demo/calls/{call_id}/turns")
    def demo_turn(call_id: str, body: TurnIn):
        try:
            return service.turn(call_id, body.text)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Call not found") from exc

    @app.post("/api/admin/reset")
    def reset_demo():
        return service.reset_and_seed(seed_demo)

    @app.post("/api/voice/twilio/incoming")
    async def twilio_incoming(request: Request):
        form = await _form(request)
        if not _authorized(request, form):
            return Response(status_code=403)
        if use_media_stream(config, settings):
            xml = stream_twiml(stream_ws_url(request, settings))
            return Response(content=xml, media_type="application/xml")
        call_sid = form.get("CallSid") or None
        started = service.start("twilio", external_id=call_sid)
        xml = gather_twiml(started["say"], _gather_action(request), config.gather_voice)
        return Response(content=xml, media_type="application/xml")

    @app.post("/api/voice/twilio/gather")
    async def twilio_gather(request: Request):
        form = await _form(request)
        if not _authorized(request, form):
            return Response(status_code=403)
        call_sid = form.get("CallSid") or None
        call_id = store.get_call_by_external(call_sid) if call_sid else None
        speech = (form.get("SpeechResult") or "").strip()
        if call_id is None:
            started = service.start("twilio", external_id=call_sid)
            call_id = started["id"]
            if not speech:
                result = started
            else:
                result = service.turn(call_id, speech)
        elif not speech:
            result = {
                "say": "I didn't catch that. What's going on at the property?",
                "outcome": None,
            }
        else:
            result = service.turn(call_id, speech)
        voice = config.gather_voice
        if result.get("outcome") == "escalated":
            xml = dial_twiml(result["say"], config.on_call_phone, voice)
        elif result.get("outcome"):
            xml = say_and_hangup(result["say"], voice)
        else:
            xml = gather_twiml(result["say"], _gather_action(request), voice)
        return Response(content=xml, media_type="application/xml")

    @app.websocket("/api/voice/stream")
    async def media_stream(websocket: WebSocket):
        await websocket.accept()
        bridge = bridge_from_settings(service, settings)
        try:
            while True:
                raw = await websocket.receive_text()
                for message in bridge.handle(loads_message(raw)):
                    await websocket.send_text(json.dumps(message))
        except WebSocketDisconnect:
            return
        except ValueError:
            await websocket.close(code=1003)

    def _authorized(request: Request, form: dict[str, str]) -> bool:
        return signature_is_valid(
            public_url(request, settings),
            form,
            settings.twilio_auth_token or "",
            request.headers.get("X-Twilio-Signature"),
        )

    def _gather_action(request: Request) -> str:
        if settings.public_base_url:
            return settings.public_base_url.rstrip("/") + "/api/voice/twilio/gather"
        return str(request.base_url).rstrip("/") + "/api/voice/twilio/gather"

    _mount_spa(app, settings.static_dir)
    return app


async def _form(request: Request) -> dict[str, str]:
    data = await request.form()
    return {key: str(value) for key, value in data.items()}


def _mount_spa(app: FastAPI, static_dir) -> None:
    if static_dir is None:
        return
    index = static_dir / "index.html"
    if not index.exists():
        return
    root = static_dir.resolve()

    @app.get("/", include_in_schema=False)
    def spa_index():
        return FileResponse(index)

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_files(full_path: str):
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (static_dir / full_path).resolve()
        if not str(candidate).startswith(str(root)) or not candidate.is_file():
            return FileResponse(index)
        return FileResponse(candidate)


app = create_app()
