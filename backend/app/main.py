"""HTTP surface: browser demo, dispatch APIs, and Twilio voice."""

from __future__ import annotations

import json
import logging
import threading
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

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
    stream_secret,
    stream_token_valid,
    stream_twiml,
    stream_ws_url,
    use_media_stream,
)

_admin_ok: ContextVar[bool] = ContextVar("admin_ok", default=False)

logger = logging.getLogger("receptionist")

PUBLIC_API = {"/api/health"}
DEMO_ONLY = {"/api/demo/calls", "/api/admin/reset", "/api/admin/purge"}


class TurnIn(BaseModel):
    text: str = Field(max_length=2000)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or settings_from_env()
    config = load_business(settings.config_path)
    store = Store(settings.db_path)
    service = ReceptionService(config, store, settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if not settings.twilio_auth_token:
            logger.warning("TWILIO_AUTH_TOKEN is empty. Twilio signature checks are DISABLED.")
        stop_purge = threading.Event()

        def purge_loop() -> None:
            while not stop_purge.wait(24 * 60 * 60):
                if settings.retention_days > 0:
                    store.purge_before(datetime.now(config.zone) - timedelta(days=settings.retention_days))

        if settings.retention_days > 0:
            cutoff = datetime.now(config.zone) - timedelta(days=settings.retention_days)
            store.purge_before(cutoff)
            threading.Thread(target=purge_loop, daemon=True).start()
        if settings.seed_on_start and store.count_calls() == 0:
            seed_demo(service)
        yield
        stop_purge.set()
        store.close()

    app = FastAPI(title="AI Receptionist for Home Services", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
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
            "llm": settings.llm_ready,
            "stt": bool(settings.deepgram_api_key),
            "tts": bool(settings.elevenlabs_api_key),
            "twilio_signature": bool(settings.twilio_auth_token),
            "media_stream_ready": settings.media_stream_ready,
            "brain": "claude-tools" if settings.llm_ready else "rules",
            "demo_mode": settings.demo_mode,
            "model": settings.anthropic_model if settings.llm_ready else None,
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
        _require_demo()
        return service.start("simulator")

    @app.post("/api/demo/calls/{call_id}/turns")
    def demo_turn(call_id: str, body: TurnIn):
        _require_demo()
        try:
            return service.turn(call_id, body.text)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Call not found") from exc

    @app.post("/api/admin/reset")
    def reset_demo():
        _require_demo()
        return service.reset_and_seed(seed_demo)

    @app.post("/api/admin/purge")
    def purge_old():
        _require_admin()
        cutoff = datetime.now(config.zone) - timedelta(days=settings.retention_days)
        return {"purged_calls": store.purge_before(cutoff)}

    @app.post("/api/voice/twilio/incoming")
    async def twilio_incoming(request: Request):
        form = await _form(request)
        if not _authorized(request, form):
            return Response(status_code=403)
        if use_media_stream(config, settings):
            xml = stream_twiml(stream_ws_url(request, settings))
            return Response(content=xml, media_type="application/xml")
        call_sid = form.get("CallSid") or None
        started = service.start("twilio", external_id=call_sid, caller_id=form.get("From"))
        xml = gather_twiml(started["say"], _gather_action(request), config.gather_voice, _language(started))
        return Response(content=xml, media_type="application/xml")

    @app.post("/api/voice/twilio/gather")
    async def twilio_gather(request: Request):
        form = await _form(request)
        if not _authorized(request, form):
            return Response(status_code=403)
        call_sid = form.get("CallSid") or None
        caller = form.get("From")
        call_id = store.get_call_by_external(call_sid) if call_sid else None
        speech = (form.get("SpeechResult") or "").strip()[:2000]
        if call_id is None:
            started = service.start("twilio", external_id=call_sid, caller_id=caller)
            call_id = started["id"]
            result = started if not speech else service.turn(call_id, speech, caller_id=caller)
        else:
            result = service.turn(call_id, speech, caller_id=caller)
        voice = _voice(result)
        language = _language(result)
        if result.get("outcome") == "escalated":
            xml = dial_twiml(result["say"], config.on_call_phone, voice, _dial_action(request), config.phone_e164)
        elif result.get("outcome"):
            xml = say_and_hangup(result["say"], voice)
        else:
            xml = gather_twiml(result["say"], _gather_action(request), voice, language)
        return Response(content=xml, media_type="application/xml")

    @app.post("/api/voice/twilio/dial-status")
    async def twilio_dial_status(request: Request):
        form = await _form(request)
        if not _authorized(request, form):
            return Response(status_code=403)
        status = (form.get("DialCallStatus") or "").lower()
        voice = config.gather_voice
        if status in {"no-answer", "busy", "failed", "canceled"}:
            from app.integrations import send_sms

            page = send_sms(
                settings,
                config.on_call_phone,
                f"{config.name}: missed transfer from {form.get('From') or 'unknown'}. Please call them back.",
            )
            service.store.add_event(
                form.get("CallSid"),
                "page",
                {"to": config.on_call_phone, "delivery": page["status"], "detail": page.get("detail")},
                page["status"],
                datetime.now(config.zone),
            )
            if page["status"] == "sent":
                say = (
                    f"{config.on_call_name} didn't pick up. The on-call tech is being paged. "
                    "If you smell gas, leave the house and call 911."
                )
            else:
                say = (
                    f"{config.on_call_name} didn't pick up. If you smell gas, leave the house and call 911. "
                    "We have not sent a text. Please call the shop again if you still need a person."
                )
            return Response(content=say_and_hangup(say, voice), media_type="application/xml")
        return Response(content=say_and_hangup("Thanks for holding. Goodbye.", voice), media_type="application/xml")

    @app.websocket("/api/voice/stream")
    async def media_stream(websocket: WebSocket):
        if not _stream_allowed(websocket):
            await websocket.close(code=1008)
            return
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

    def _dial_action(request: Request) -> str:
        if settings.public_base_url:
            return settings.public_base_url.rstrip("/") + "/api/voice/twilio/dial-status"
        return str(request.base_url).rstrip("/") + "/api/voice/twilio/dial-status"

    def _language(result: dict) -> str:
        if result.get("language") == "es":
            return "es-US"
        return config.gather_language

    def _voice(result: dict) -> str:
        if result.get("language") == "es":
            return "Polly.Lupe"
        return config.gather_voice

    def _require_demo() -> None:
        if not settings.demo_mode:
            raise HTTPException(status_code=404, detail="Not found")

    def _require_admin() -> None:
        if settings.demo_mode:
            return
        if not _admin_ok.get():
            raise HTTPException(status_code=401, detail="Admin token required")

    def _stream_allowed(websocket: WebSocket) -> bool:
        token = websocket.query_params.get("token") or ""
        secret = stream_secret(settings)
        if secret and stream_token_valid(secret, token):
            return True
        if settings.demo_mode and not token:
            return True
        return False

    @app.middleware("http")
    async def guard_api(request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/") and request.method != "OPTIONS":
            length = request.headers.get("content-length")
            if length and length.isdigit() and int(length) > 100_000:
                return JSONResponse(status_code=413, content={"detail": "Request too large"})
            _admin_ok.set(False)
            if path not in PUBLIC_API and not path.startswith("/api/voice/twilio"):
                if not settings.demo_mode:
                    header = request.headers.get("authorization") or ""
                    token = header.removeprefix("Bearer ").strip()
                    if not settings.admin_token or token != settings.admin_token:
                        return JSONResponse(status_code=401, content={"detail": "Admin token required"})
                    _admin_ok.set(True)
                else:
                    _admin_ok.set(True)
        return await call_next(request)

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
