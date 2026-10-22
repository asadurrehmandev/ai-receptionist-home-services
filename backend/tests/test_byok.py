"""A visitor key is used for one turn and then forgotten.

The secret must not show up in the response, the logs, the database, or any
file the desk writes.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi.testclient import TestClient

from app.agent.engine import SessionState
from app.config_loader import load_business
from app.llm.claude import ClaudeClient
from app.llm.keys import LlmRefused
from app.main import create_app
from app.service import ReceptionService
from app.settings import Settings
from app.store import Store

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "business.yaml"
SECRET = "sk-ant-TESTKEY-9f3c2a-do-not-store"


def _settings(tmp_path) -> Settings:
    return Settings(
        config_path=CONFIG,
        db_path=tmp_path / "desk.db",
        static_dir=None,
        seed_on_start=False,
        demo_mode=True,
    )


def test_a_safety_yes_never_reaches_the_model(tmp_path):
    class Grabby:
        provider = "anthropic"

        def __init__(self) -> None:
            self.calls = 0

        def complete(self, messages, tools, timeout=None):
            self.calls += 1
            return {
                "stop_reason": "tool_use",
                "content": [{"type": "tool_use", "id": "1", "name": "speak", "input": {"intent": "goodbye"}}],
            }

    grabby = Grabby()
    settings = _settings(tmp_path)
    settings.model_client = grabby
    service = ReceptionService(load_business(CONFIG), Store(settings.db_path), settings)
    state = SessionState(phase="hazard_check", issue="odd smell")
    result = service.dialog.handle(state, "Yes, we already stepped outside.")
    assert grabby.calls == 0
    assert state.outcome == "escalated"
    assert "miguel" in result.say.lower()
    service.store.close()


def test_a_refused_key_falls_back_and_is_not_stored(tmp_path, caplog, monkeypatch):
    def complete(self, messages, tools, timeout=None):
        logging.getLogger("httpx").warning("provider rejected %s", SECRET)
        raise LlmRefused("The key was refused or has no quota.")

    monkeypatch.setattr(ClaudeClient, "complete", complete)
    settings = _settings(tmp_path)
    application = create_app(settings)
    caplog.set_level(logging.DEBUG)
    with TestClient(application) as client:
        started = client.post("/api/demo/calls")
        assert started.status_code == 200
        call_id = started.json()["id"]
        response = client.post(
            f"/api/demo/calls/{call_id}/turns",
            json={"text": "I want the yearly heat pump check."},
            headers={"X-LLM-Key": SECRET, "X-LLM-Provider": "anthropic"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["reply_source"] == "demo"
    assert body["mode_note"]
    assert "sample" in body["mode_note"].lower()
    assert "name" in body["say"].lower()
    assert "claude" not in body["say"].lower()
    assert "gpt" not in body["say"].lower()
    blob = response.text + caplog.text
    assert SECRET not in blob
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes()
    assert SECRET not in settings.db_path.read_bytes().decode("utf-8", errors="ignore")
