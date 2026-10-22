"""HTTP surface: browser demo, dispatch APIs, and Twilio voice."""

from __future__ import annotations

import concurrent.futures
import json
import logging
import threading
from uuid import uuid4
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from app.agent.hazard_nli import nli_ready
from app.agent.hazard_semantic import semantic_ready
from app.agent.understand import classifier_mode, understand_ready, understander_name
from app.config_loader import load_business
from app.integrations import deliver_webhook
from app.llm.keys import redacted
from app.seed import seed_demo
from app.service import ReceptionService
from app.settings import Settings, settings_from_env
from app.store import Store
from app.voice.stream import bridge_from_settings, loads_message
from app.voice.twilio import (
    dial_twiml,
    filler_then_redirect,
    gather_twiml,
    public_url,
    say_and_hangup,
    consume_stream_token,
    mint_stream_token,
    signature_is_valid,
    stream_secret,
    stream_twiml,
    stream_ws_url,
    use_media_stream,
)

_admin_ok: ContextVar[bool] = ContextVar("admin_ok", default=False)

logger = logging.getLogger("receptionist")
_turn_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
_pending_turns: dict[str, concurrent.futures.Future] = {}

PUBLIC_API = {"/api/health"}
DEMO_ONLY = {"/api/demo/calls", "/api/admin/reset", "/api/admin/purge"}


class TurnIn(BaseModel):
    text: str = Field(max_length=2000)


def _session_llm(request: Request) -> tuple[str | None, str | None]:
    """Read a visitor key from headers. Never log the header map."""
    key = (request.headers.get("x-llm-key") or "").strip()
    hinted = (request.headers.get("x-llm-provider") or "").strip().lower()
    if hinted not in {"anthropic", "openai"}:
        hinted = None
    if not key:
        return None, None
    return key, hinted


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
        allow_headers=["Authorization", "Content-Type", "X-LLM-Key", "X-LLM-Provider"],
    )
    app.state.settings = settings
    app.state.config = config
    app.state.store = store
    app.state.service = service

    @app.get("/api/health")
    def health():
        semantic = semantic_ready()
        nli = nli_ready()
        degraded = [name for name, ready_flag in (("semantic", semantic), ("nli", nli)) if not ready_flag]
        ready = not degraded
        body = {
            "ok": ready,
            "business": config.name,
            "llm": settings.llm_ready,
            "stt": bool(settings.deepgram_api_key),
            "tts": bool(settings.elevenlabs_api_key),
            "twilio_signature": bool(settings.twilio_auth_token),
            "media_stream_ready": settings.media_stream_ready,
            "brain": "claude-tools" if settings.env_llm_provider == "anthropic" else (
                "openai-tools" if settings.env_llm_provider == "openai" else "rules"
            ),
            "classifier": classifier_mode(),
            "demo_mode": settings.demo_mode,
            "model": (
                settings.anthropic_model
                if settings.env_llm_provider == "anthropic"
                else settings.openai_model
                if settings.env_llm_provider == "openai"
                else None
            ),
            "reply_mode": "live" if settings.env_llm_provider else "demo",
            "llm_provider": settings.env_llm_provider,
            "voice_ready": _voice_block_reason() is None,
            "voice_block_reason": _voice_block_reason(),
            "semantic_ready": semantic,
            "nli_ready": nli,
            "understand_ready": understand_ready(),
            "understander": understander_name(),
            "degraded": degraded,
        }
        if not ready:
            return JSONResponse(status_code=503, content=body)
        return body

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
    def demo_turn(call_id: str, body: TurnIn, request: Request):
        _require_demo()
        session_key, session_provider = _session_llm(request)
        try:
            with redacted(session_key):
                return service.turn(
                    call_id,
                    body.text,
                    session_key=session_key,
                    session_provider=session_provider,
                )
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
        blocked = _voice_block_reason()
        if blocked:
            return JSONResponse(status_code=503, content={"detail": blocked})
        form = await _form(request)
        if not _authorized(request, form):
            return Response(status_code=403)
        if use_media_stream(config, settings):
            secret = stream_secret(settings)
            token = mint_stream_token(secret) if secret else None
            xml = stream_twiml(stream_ws_url(request, settings), token)
            return Response(content=xml, media_type="application/xml")
        call_sid = form.get("CallSid") or None
        started = service.start("twilio", external_id=call_sid, caller_id=form.get("From"))
        xml = gather_twiml(started["say"], _gather_action(request), config.gather_voice, _language(started))
        return Response(content=xml, media_type="application/xml")

    def _wants_filler(speech: str) -> bool:
        """Keyless turns stay on the keyword screen, so the gather does not say 'One moment.'"""
        return False

    @app.post("/api/voice/twilio/gather")
    async def twilio_gather(request: Request):
        blocked = _voice_block_reason()
        if blocked:
            return JSONResponse(status_code=503, content={"detail": blocked})
        form = await _form(request)
        if not _authorized(request, form):
            return Response(status_code=403)
        call_sid = form.get("CallSid") or None
        caller = form.get("From")
        call_id = store.get_call_by_external(call_sid) if call_sid else None
        speech = (form.get("SpeechResult") or "").strip()[:2000]
        resume = request.query_params.get("resume") == "1"
        pending_key = call_sid or ""
        if resume and pending_key in _pending_turns:
            future = _pending_turns.pop(pending_key)
            try:
                result = future.result(timeout=12)
            except Exception:
                logger.exception("Understander turn failed")
                result = {
                    "say": "I couldn't check that safely. Is anyone in danger right now, or would you like a person to call you back?",
                    "outcome": None,
                    "language": "en",
                }
        else:
            if call_id is None:
                started = service.start("twilio", external_id=call_sid, caller_id=caller)
                call_id = started["id"]
                if not speech:
                    result = started
                elif _wants_filler(speech):
                    _pending_turns[pending_key or call_id] = _turn_pool.submit(
                        service.turn, call_id, speech, caller
                    )
                    action = _gather_action(request) + "?resume=1"
                    xml = filler_then_redirect(action, config.gather_voice)
                    return Response(content=xml, media_type="application/xml")
                else:
                    result = service.turn(call_id, speech, caller_id=caller)
            elif _wants_filler(speech):
                _pending_turns[pending_key or call_id] = _turn_pool.submit(
                    service.turn, call_id, speech, caller
                )
                action = _gather_action(request) + "?resume=1"
                xml = filler_then_redirect(action, config.gather_voice)
                return Response(content=xml, media_type="application/xml")
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
        blocked = _voice_block_reason()
        if blocked:
            return JSONResponse(status_code=503, content={"detail": blocked})
        form = await _form(request)
        if not _authorized(request, form):
            return Response(status_code=403)
        status = (form.get("DialCallStatus") or "").lower()
        voice = config.gather_voice
        if status in {"no-answer", "busy", "failed", "canceled"}:
            from app.integrations import send_sms

            leg = request.query_params.get("leg") or ""
            if config.on_call_phone_2 and leg != "2":
                action = _dial_action(request) + "?leg=2"
                xml = dial_twiml(
                    f"{config.on_call_name} didn't pick up. I'm trying the backup on-call number.",
                    config.on_call_phone_2,
                    voice,
                    action,
                    config.phone_e164,
                )
                return Response(content=xml, media_type="application/xml")
            page = send_sms(
                settings,
                config.on_call_phone,
                f"{config.name}: missed transfer from {form.get('From') or 'unknown'}. Please call them back.",
            )
            now = datetime.now(config.zone)
            call_sid = form.get("CallSid")
            service.store.add_event(
                call_sid,
                "page",
                {"to": config.on_call_phone, "delivery": page["status"], "detail": page.get("detail")},
                page["status"],
                now,
            )
            call_id = store.get_call_by_external(call_sid) if call_sid else None
            caller_state = None
            if call_id:
                try:
                    caller_state = store.load_state(call_id)
                except Exception:
                    caller_state = None
            hazard = _caller_hazard(call_sid)
            lead = {
                "id": "ld_" + uuid4().hex[:10],
                "call_id": call_id,
                "name": caller_state.name if caller_state else None,
                "phone": form.get("From"),
                "address": caller_state.address if caller_state else None,
                "issue": hazard or "Missed transfer",
                "intent": "handoff",
                "status": "missed_transfer",
            }
            store.upsert_lead(lead, now)
            hook = {
                "event": "call.transfer_missed",
                "business": config.name,
                "source": "ai_receptionist",
                "call_id": call_id,
                "contact": {"name": lead["name"], "phone": lead["phone"], "address": lead["address"]},
                "reason": hazard or "Missed transfer",
            }
            delivery = deliver_webhook(config.webhook_url, hook, settings.webhook_secret)
            store.add_event(call_id or call_sid, "webhook", {**hook, "delivery": delivery}, delivery["status"], now)
            spanish = _caller_language(call_sid) == "es"
            guidance = _missed_guidance(hazard, spanish)
            if settings.demo_mode:
                promised = page["status"] == "sent" or delivery["status"] in {"mock", "delivered"}
            else:
                promised = page["status"] == "sent" or delivery["status"] == "delivered"
            if promised:
                callback = "Una persona le devolverá la llamada." if spanish else "Someone from the office will call you back."
            else:
                callback = (
                    "La llamada quedó registrada para la oficina. Llame al 911 si alguien está en peligro."
                    if spanish
                    else "The call has been logged for the office. Call 911 if anyone is in danger."
                )
            if page["status"] == "sent":
                lead = (
                    f"{config.on_call_name} no contestó. Estamos avisando al técnico de guardia."
                    if spanish
                    else f"{config.on_call_name} didn't pick up. The on-call tech is being paged."
                )
            else:
                lead = (
                    f"{config.on_call_name} no contestó."
                    if spanish
                    else f"{config.on_call_name} didn't pick up."
                )
            honest = "" if page["status"] == "sent" else (" No hemos enviado un mensaje." if spanish else " We have not sent a text.")
            say = f"{lead} {guidance} {callback}{honest}"
            return Response(content=say_and_hangup(say, "Polly.Lupe" if spanish else voice), media_type="application/xml")
        return Response(content=say_and_hangup("Thanks for holding. Goodbye.", voice), media_type="application/xml")

    @app.websocket("/api/voice/stream")
    async def media_stream(websocket: WebSocket):
        if _voice_block_reason():
            await websocket.close(code=1008)
            return
        await websocket.accept()
        bridge = bridge_from_settings(service, settings)
        authorized = bool(settings.demo_mode)
        secret = stream_secret(settings)
        try:
            while True:
                raw = await websocket.receive_text()
                message = loads_message(raw)
                if not authorized:
                    if message.get("event") == "connected":
                        continue
                    token = ""
                    if message.get("event") == "start":
                        custom = (message.get("start") or {}).get("customParameters") or {}
                        token = str(custom.get("token") or "")
                    if not consume_stream_token(secret, token):
                        await websocket.close(code=1008)
                        return
                    authorized = True
                for frame in bridge.handle(message):
                    await websocket.send_text(json.dumps(frame))
        except WebSocketDisconnect:
            return
        except ValueError:
            await websocket.close(code=1003)

    def _voice_block_reason() -> str | None:
        if settings.demo_mode:
            return None
        if not settings.twilio_auth_token:
            return "Voice will not start without TWILIO_AUTH_TOKEN when DEMO_MODE=0."
        return None

    def _authorized(request: Request, form: dict[str, str]) -> bool:
        return signature_is_valid(
            public_url(request, settings),
            form,
            settings.twilio_auth_token or "",
            request.headers.get("X-Twilio-Signature"),
            allow_unsigned=settings.demo_mode,
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

    def _caller_hazard(call_sid: str | None) -> str | None:
        if not call_sid:
            return None
        call_id = store.get_call_by_external(call_sid)
        if not call_id:
            return None
        try:
            return store.load_state(call_id).hazard
        except Exception:
            return None

    def _caller_language(call_sid: str | None) -> str:
        if not call_sid:
            return "en"
        call_id = store.get_call_by_external(call_sid)
        if not call_id:
            return "en"
        try:
            return store.load_state(call_id).language or "en"
        except Exception:
            return "en"

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


def _missed_guidance(hazard: str | None, spanish: bool) -> str:
    label = (hazard or "").lower()
    if "carbon" in label:
        return (
            "Saquen a todos afuera, al aire libre, y llamen al 911."
            if spanish
            else "Get everyone outside into fresh air and call 911."
        )
    if "water" in label or "flood" in label:
        return (
            "Si puede hacerlo sin riesgo, cierre la llave principal del agua."
            if spanish
            else "If you can do it safely, shut the main water valve."
        )
    if "electrical" in label:
        return (
            "Aléjese y llame al 911 si hay humo o fuego."
            if spanish
            else "Stay away from it and call 911 if you see smoke or fire."
        )
    if "temperature" in label or "comfort" in label:
        return (
            "Mantenga a las personas vulnerables en un lugar tibio o fresco, y llame al 911 si se sienten mal."
            if spanish
            else "Keep anyone vulnerable warm or cool, and call 911 if they are unwell."
        )
    return (
        "Si huele a gas, salga de la casa y llame al 911 o a la compañía de gas."
        if spanish
        else "If you smell gas, leave the house and call 911 or your gas company."
    )


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
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_files(full_path: str):
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (static_dir / full_path).resolve()
        if not str(candidate).startswith(str(root)) or not candidate.is_file():
            return FileResponse(index)
        return FileResponse(candidate)


app = create_app()
