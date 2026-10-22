"""HTTP demo, Twilio webhooks, CRM log, and media-stream framing."""

from __future__ import annotations

import base64
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.integrations import MissingKey, synthesize_ulaw, transcribe_mulaw
from app.agent.facts import speech_supported
from app.main import create_app
from app.seed import seed_demo
from app.service import FixedClock, ReceptionService
from app.settings import Settings
from app.store import Store
from app.voice.stream import MediaBridge
from app.voice.twilio import twilio_signature
from app.config_loader import load_business

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def client(tmp_path):
    settings = Settings(
        config_path=ROOT / "config" / "business.yaml",
        db_path=tmp_path / "test.db",
        static_dir=None,
        seed_on_start=False,
    )
    application = create_app(settings)
    with TestClient(application) as test_client:
        yield test_client


def _require_hazard_models() -> None:
    from app.agent.hazard_nli import nli_ready
    from app.agent.hazard_semantic import semantic_ready

    if not (semantic_ready() and nli_ready()):
        pytest.skip("MiniLM and DeBERTa NLI weights are not on disk. Run python scripts/fetch_models.py")


def test_health_reports_rule_brain(client):
    _require_hazard_models()
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["brain"] == "rules"
    assert body["classifier"] == "e5-head"
    assert body["hazard_screen"] == "head+rules+minilm+nli"
    assert body["understander"] == "off"
    assert body["voice_ready"] is False
    assert "not a live phone" in body["voice_block_reason"]
    assert body["understand_ready"] is False
    assert body["degraded"] == []
    assert body["llm"] is False
    assert body["reply_mode"] == "demo"
    assert body["llm_provider"] is None
    assert body["media_stream_ready"] is False
    assert "Northline" in body["business"]


def test_demo_call_books_and_logs_webhook(client):
    started = client.post("/api/demo/calls")
    assert started.status_code == 200
    call_id = started.json()["id"]
    assert "virtual receptionist" in started.json()["say"]
    lines = [
        "My kitchen drain is clogged and backing up into the sink.",
        "Jordan Hale",
        "512-555-0164",
        "880 West Mary Street, Austin 78704",
        "the earliest you have",
        "yes",
    ]
    last = None
    for line in lines:
        last = client.post(f"/api/demo/calls/{call_id}/turns", json={"text": line})
        assert last.status_code == 200
        assert last.json()["latency_ms"] < 250
    assert last is not None
    body = last.json()
    assert body["outcome"] == "booked"
    assert "You're booked" in body["say"]
    detail = client.get(f"/api/calls/{call_id}").json()
    roles = [turn["role"] for turn in detail["turns"]]
    assert roles[0] == "agent"
    assert "caller" in roles
    assert any(event["type"] == "sms" for event in detail["events"])
    webhook = next(event for event in detail["events"] if event["type"] == "webhook")
    assert webhook["payload"]["event"] == "job.booked"
    assert webhook["payload"]["delivery"]["status"] == "mock"
    assert webhook["payload"]["contact"]["name"] == "Jordan Hale"
    metrics = client.get("/api/metrics").json()
    assert metrics["count"] >= 1
    assert metrics["p95_ms"] < 250
    overview = client.get("/api/overview").json()
    assert overview["counts"]["booked"] >= 1
    assert overview["upcoming"]


def test_twilio_gather_escalates_with_dial(client):
    incoming = client.post("/api/voice/twilio/incoming", data={"CallSid": "CA123", "From": "+15125550177"})
    assert incoming.status_code == 200
    xml = incoming.text
    assert "<Gather" in xml
    assert 'timeout="5"' in xml
    assert 'actionOnEmptyResult="true"' in xml
    assert "Northline Plumbing" in xml
    assert "<Stream" not in xml
    gathered = client.post(
        "/api/voice/twilio/gather",
        data={"CallSid": "CA123", "SpeechResult": "I smell gas in the laundry room."},
    )
    assert gathered.status_code == 200
    assert "<Number>+15125550199</Number>" in gathered.text
    assert 'timeout="20"' in gathered.text
    assert "dial-status" in gathered.text
    assert "Miguel" in gathered.text


def test_twilio_signature_rejects_bad_and_accepts_good(tmp_path):
    settings = Settings(
        config_path=ROOT / "config" / "business.yaml",
        db_path=tmp_path / "sig.db",
        static_dir=None,
        seed_on_start=False,
        twilio_auth_token="12345",
    )
    with TestClient(create_app(settings)) as client:
        params = {"CallSid": "CA1", "From": "+15125550000"}
        url = "http://testserver/api/voice/twilio/incoming"
        bad = client.post("/api/voice/twilio/incoming", data=params, headers={"X-Twilio-Signature": "nope"})
        assert bad.status_code == 403
        signature = twilio_signature(url, params, "12345")
        good = client.post(
            "/api/voice/twilio/incoming",
            data=params,
            headers={"X-Twilio-Signature": signature},
        )
        assert good.status_code == 200
        assert "<Gather" in good.text


def test_media_stream_speaks_and_marks_transfer(tmp_path):
    settings = Settings(
        config_path=ROOT / "config" / "business.yaml",
        db_path=tmp_path / "stream.db",
        static_dir=None,
        seed_on_start=False,
    )
    config = load_business(settings.config_path)
    store = Store(settings.db_path)
    service = ReceptionService(config, store, settings)
    audio = b"\xff" * 320

    def synthesize(_text: str) -> bytes:
        return audio

    bridge = MediaBridge(service, synthesize=synthesize, transcribe=lambda _audio: "I smell gas")
    frames = bridge.handle({"event": "start", "start": {"streamSid": "MZ1", "callSid": "CA9"}})
    assert frames[0]["event"] == "clear"
    assert frames[1]["event"] == "media"
    payload = base64.b64decode(frames[1]["media"]["payload"])
    assert payload == b"\xff" * 160
    follow = bridge.apply_transcript("I smell gas in the kitchen at 18 Rio Grande Street, Austin 78701.")
    assert any(frame.get("event") == "mark" and frame["mark"]["name"] == "transfer" for frame in follow)
    call = store.get_call(bridge.call_id)
    assert call["outcome"] == "escalated"
    store.close()


def test_media_stream_without_keys_marks_configuration(client):
    with client.websocket_connect("/api/voice/stream") as socket:
        socket.send_json({"event": "start", "start": {"streamSid": "MZ2", "callSid": "CA8"}})
        first = socket.receive_json()
        second = socket.receive_json()
        names = {first["mark"]["name"], second["mark"]["name"]}
        assert "tts-unconfigured" in names
        socket.send_json({"event": "stop"})
        stopped = socket.receive_json()
        assert stopped["mark"]["name"] == "stt-unconfigured"


def test_stream_mode_selected_when_keys_present(tmp_path):
    gather_only = Settings(
        config_path=ROOT / "config" / "business.yaml",
        db_path=tmp_path / "keys.db",
        static_dir=None,
        seed_on_start=False,
        deepgram_api_key="dg_test",
        elevenlabs_api_key="el_test",
        public_base_url="https://desk.example.com",
    )
    with TestClient(create_app(gather_only)) as client:
        response = client.post("/api/voice/twilio/incoming", data={"CallSid": "CA55"})
        assert response.status_code == 200
        assert "<Gather" in response.text
        assert "<Stream" not in response.text
        health = client.get("/api/health").json()
        assert health["media_stream_ready"] is True
        assert health["semantic_ready"] is True
        assert health["brain"] == "rules"
    streaming = Settings(
        config_path=ROOT / "config" / "business.yaml",
        db_path=tmp_path / "stream.db",
        static_dir=None,
        seed_on_start=False,
        deepgram_api_key="dg_test",
        elevenlabs_api_key="el_test",
        twilio_account_sid="AC_test",
        twilio_auth_token="tok",
        public_base_url="https://desk.example.com",
    )
    with TestClient(create_app(streaming)) as client:
        form = {"CallSid": "CA56"}
        signed = twilio_signature("https://desk.example.com/api/voice/twilio/incoming", form, "tok")
        response = client.post(
            "/api/voice/twilio/incoming",
            data=form,
            headers={"X-Twilio-Signature": signed},
        )
        assert response.status_code == 200
        assert "wss://desk.example.com/api/voice/stream" in response.text


def test_seed_scripts_and_reset(tmp_path):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    settings = Settings(
        config_path=ROOT / "config" / "business.yaml",
        db_path=tmp_path / "seed.db",
        static_dir=None,
        seed_on_start=False,
    )
    config = load_business(settings.config_path)
    store = Store(settings.db_path)
    clock = FixedClock(datetime(2026, 10, 21, 10, 0, tzinfo=ZoneInfo("America/Chicago")))
    service = ReceptionService(config, store, settings, clock=clock)
    seed_demo(service)
    from datetime import timedelta

    calls = store.list_calls()
    stamps = [datetime.fromisoformat(call["started_at"]) for call in calls]
    assert max(stamps) - min(stamps) >= timedelta(hours=6)
    for call in calls:
        span = datetime.fromisoformat(call["ended_at"]) - datetime.fromisoformat(call["started_at"])
        assert timedelta(minutes=2) <= span <= timedelta(minutes=6)
    lena = next(call for call in calls if call["caller_name"] == "Lena Ortiz")
    assert lena["issue"] == "Burst pipe"
    assert lena["outcome"] == "escalated"
    counts = store.outcome_counts()
    assert counts.get("booked", 0) >= 3
    assert counts.get("escalated", 0) >= 1
    assert counts.get("spam", 0) >= 1
    assert counts.get("missed", 0) >= 1
    assert any(booking["name"] == "Dana Cho" for booking in store.list_bookings())
    service.reset_and_seed(seed_demo)
    assert store.count_calls() == 7
    store.close()


def test_deepgram_and_elevenlabs_clients():
    def deepgram(request: httpx.Request) -> httpx.Response:
        assert "mulaw" in str(request.url)
        assert request.headers["authorization"] == "Token dg_test"
        return httpx.Response(
            200,
            json={"results": {"channels": [{"alternatives": [{"transcript": "burst pipe"}]}]}},
        )

    def eleven(request: httpx.Request) -> httpx.Response:
        assert request.headers["xi-api-key"] == "el_test"
        assert request.url.params["output_format"] == "ulaw_8000"
        return httpx.Response(200, content=b"\xff" * 160)

    with httpx.Client(transport=httpx.MockTransport(deepgram)) as deepgram_client:
        assert transcribe_mulaw(b"\x00\x01", "dg_test", deepgram_client) == "burst pipe"
    with httpx.Client(transport=httpx.MockTransport(eleven)) as eleven_client:
        assert synthesize_ulaw("You're booked", "el_test", "voice", eleven_client) == b"\xff" * 160
    with pytest.raises(MissingKey):
        transcribe_mulaw(b"\x00", "")
    allowed = "Wednesday, October 22 at 11:30 AM for $89"
    assert speech_supported("See you Wednesday at 11:30 AM, the visit is $89.", allowed)
    assert not speech_supported("You're booked for Saturday, October 31 at 11:30 AM", allowed)
    assert not speech_supported(allowed + " We can also do it for $99 at 6:30 PM.", allowed)
    assert not speech_supported("No need to worry, this doesn't sound like an emergency.", allowed, emergency=True)
