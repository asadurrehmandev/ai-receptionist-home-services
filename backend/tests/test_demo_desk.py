"""Regression tests for the Porter demo desk (simulator UX, seeds, escalation capture)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.config_loader import load_business
from app.main import create_app
from app.seed import seed_demo
from app.service import FixedClock, ReceptionService
from app.settings import Settings
from app.store import Store

ROOT = Path(__file__).resolve().parents[2]
GAS_LINE = (
    "I smell gas in the laundry room at 18 Rio Grande Street, Austin 78701. "
    "I'm Chris Patel, 512-555-0108."
)
ZONE = ZoneInfo("America/Chicago")


def _client(tmp_path) -> TestClient:
    settings = Settings(
        config_path=ROOT / "config" / "business.yaml",
        db_path=tmp_path / "desk.db",
        static_dir=None,
        seed_on_start=False,
    )
    return TestClient(create_app(settings))


def test_escalation_captures_contact_from_a_one_line_gas_turn(tmp_path):
    with _client(tmp_path) as client:
        started = client.post("/api/demo/calls")
        assert started.status_code == 200
        call_id = started.json()["id"]
        body = client.post(f"/api/demo/calls/{call_id}/turns", json={"text": GAS_LINE}).json()
        assert body["outcome"] == "escalated"
        assert body["slots"]["name"] == "Chris Patel"
        assert body["slots"]["phone"] == "5125550108"
        assert "78701" in (body["slots"]["address"] or "")
        lead = next(event for event in body["events"] if event["type"] == "lead")
        payload = lead["payload"]
        assert payload["name"] == "Chris Patel"
        assert payload["phone"] == "(512) 555-0108"
        assert payload["address"]
        webhook = next(event for event in body["events"] if event["type"] == "webhook")
        contact = webhook["payload"]["contact"]
        assert contact["name"] == "Chris Patel"
        assert contact["phone"] == "(512) 555-0108"


def test_a_hazard_after_a_booked_call_still_gets_a_safety_line(tmp_path):
    with _client(tmp_path) as client:
        started = client.post("/api/demo/calls")
        call_id = started.json()["id"]
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
            last = client.post(f"/api/demo/calls/{call_id}/turns", json={"text": line}).json()
        assert last["outcome"] == "booked"
        follow = client.post(
            f"/api/demo/calls/{call_id}/turns",
            json={"text": "Actually I smell gas in the laundry room now."},
        ).json()
        lowered = follow["say"].lower()
        assert "call has ended" not in lowered
        assert "gas" in lowered or "danger" in lowered or "emergency" in lowered


def test_seed_timestamps_are_in_the_past_in_shop_time(tmp_path):
    moment = datetime(2026, 10, 24, 11, 30, tzinfo=ZONE)
    settings = Settings(
        config_path=ROOT / "config" / "business.yaml",
        db_path=tmp_path / "seed.db",
        static_dir=None,
        seed_on_start=False,
    )
    config = load_business(settings.config_path)
    store = Store(settings.db_path)
    service = ReceptionService(config, store, settings, clock=FixedClock(moment))
    seed_demo(service)
    stamps = [datetime.fromisoformat(call["started_at"]) for call in store.list_calls()]
    assert stamps
    assert all(stamp <= moment for stamp in stamps)
    assert max(stamps) - min(stamps) >= timedelta(hours=4)
    store.close()


def test_a_fresh_simulator_call_sorts_ahead_of_seeded_calls(tmp_path):
    moment = datetime(2026, 10, 24, 11, 30, tzinfo=ZONE)
    settings = Settings(
        config_path=ROOT / "config" / "business.yaml",
        db_path=tmp_path / "sort.db",
        static_dir=None,
        seed_on_start=False,
    )
    config = load_business(settings.config_path)
    store = Store(settings.db_path)
    clock = FixedClock(moment)
    service = ReceptionService(config, store, settings, clock=clock)
    seed_demo(service)
    live = service.start("simulator")
    calls = store.list_calls()
    assert calls[0]["id"] == live["id"]
    assert datetime.fromisoformat(calls[0]["started_at"]) == moment
    store.close()


def test_hazard_stack_warms_without_error():
    from app.agent.hazard_head import warm_hazard_stack

    warm_hazard_stack()
