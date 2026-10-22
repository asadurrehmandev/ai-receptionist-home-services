"""A missing hazard model must not kill startup, and it must not page a drain call."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.agent.hazard import classify_emergency
from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


def test_missing_weights_start_unhealthy_and_do_not_page_a_drain(tmp_path, monkeypatch):
    import app.agent.hazard_semantic as semantic

    saved = (semantic._model, semantic._load_failed, semantic._bank)
    cache = os.environ.get("FASTEMBED_CACHE_PATH")
    offline = os.environ.get("HF_HUB_OFFLINE")
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(tmp_path / "empty-weights"))
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    semantic._model = None
    semantic._load_failed = False
    semantic._bank = None
    try:
        settings = Settings(
            config_path=ROOT / "config" / "business.yaml",
            db_path=tmp_path / "degraded.db",
            static_dir=None,
            seed_on_start=True,
            demo_mode=True,
        )
        with TestClient(create_app(settings)) as client:
            health = client.get("/api/health")
            assert health.status_code == 503
            assert health.json()["semantic_ready"] is False
            service = client.app.state.service
            drain = service.start("simulator")
            last = drain
            for line in (
                "My kitchen drain is clogged and backing up into the sink.",
                "Jordan Hale",
                "512-555-0164",
                "880 West Mary Street, Austin 78704",
                "the earliest you have",
                "yes",
            ):
                last = service.turn(drain["id"], line)
            assert last["outcome"] in {"booked", "callback"}
            assert last["outcome"] != "escalated"
            gas = service.start("simulator")
            paged = service.turn(gas["id"], "I smell gas in the kitchen")
            assert paged["outcome"] == "escalated"
            level, label = classify_emergency("there is a weird smell in the closet")
            assert level == "ask" and label == "Hazard model unavailable"
    finally:
        semantic._model, semantic._load_failed, semantic._bank = saved
        if cache is None:
            os.environ.pop("FASTEMBED_CACHE_PATH", None)
        else:
            os.environ["FASTEMBED_CACHE_PATH"] = cache
        if offline is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = offline
