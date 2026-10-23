"""Round 22: a list miss is not a routine, and the desk speaks sewage stay-away.

A drip, a fixture, a drain, or a catalogue job must not zero a definite head
when words are left over. The HTTP desk, not only Engine.handle, stays away
from sewage. The held-out file was hashed before this round's policy edit.
Do not edit its lines to lift a score. Do not move the page cut.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.agent.calendar import MemoryCalendar
from app.agent.dialog import Dialog
from app.agent.engine import Engine, SessionState
from app.agent.hazard import _positive_routine, classify_emergency, prepare
from app.agent.nlu import detect_language
from app.config_loader import load_business
from app.main import create_app
from app.service import FixedClock
from app.settings import Settings
from evals.round22_heldout_set import HELDOUT

ROOT = Path(__file__).resolve().parents[2]
THU = datetime(2026, 10, 22, 9, 0, tzinfo=ZoneInfo("America/Chicago"))
CONFIG = load_business(ROOT / "config" / "business.yaml")
HELDOUT_SHA = "86c0e4fb96853e828ece19ff0d9da229aefe17dbe637f3892bd47ac4fccdea83"


def _engine() -> Engine:
    return Engine(CONFIG, MemoryCalendar(), FixedClock(THU))


def test_round22_heldout_file_is_unchanged():
    digest = hashlib.sha256((ROOT / "evals" / "round22_heldout_set.py").read_bytes()).hexdigest()
    assert digest == HELDOUT_SHA
    assert len(HELDOUT) >= 40


def test_page_cut_stays_put():
    source = (ROOT / "backend" / "app" / "agent" / "hazard_head.py").read_text()
    assert "PAGE_MIN = 0.55" in source
    assert "PAGE_MIN = 0.80" not in source
    from app.agent import hazard_head

    hazard_head._weights()
    assert round(hazard_head.PAGE_MIN, 2) == 0.55
    assert round(hazard_head.ASK_MIN, 2) == 0.55
    assert round(hazard_head.PAGE_MARGIN, 2) == 0.02
    assert round(hazard_head.ROUTINE_LOCK, 2) == 0.40


def test_leftover_words_do_not_zero_a_definite_head(monkeypatch):
    monkeypatch.setattr("app.agent.hazard_head.head_level", lambda text: ("definite", "Hazard"))
    monkeypatch.setattr("app.agent.hazard._emergency_probability", lambda text: 0.89)
    line = "The floor drain is sluggish and the corridor feels peculiar."
    assert _positive_routine(prepare(line), line) is False
    level, label = classify_emergency(line)
    assert level in {"definite", "ask"}, (level, label)
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.phase != "collect_name"
    assert state.outcome == "escalated" or state.phase == "hazard_check"
    lowered = heard.say.lower()
    assert "what's going on" not in lowered
    assert "name" not in lowered
    assert "179" not in lowered or state.outcome != "escalated" or level == "definite"


def test_a_pure_drain_still_books():
    line = "My kitchen drain is clogged and backing up into the sink."
    level, _label = classify_emergency(line)
    assert level != "definite"
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.outcome != "escalated"
    assert state.phase == "collect_name"
    assert "179" not in heard.say


def test_dialog_active_water_label_speaks_stay_away():
    """The desk stores the rules label, then escalates. The words still count."""
    state = SessionState()
    line = "Waste water is pushing up through the laundry floor drain."
    state.hazard = "Active water"
    state.hazard_text = line
    heard = _engine().handle(state, line)
    lowered = heard.say.lower()
    assert state.outcome == "escalated"
    assert "sewage" in lowered
    assert "valve" not in lowered
    assert "179" in heard.say


def test_http_desk_sewage_stays_away(tmp_path):
    settings = Settings(
        config_path=ROOT / "config" / "business.yaml",
        db_path=tmp_path / "desk.db",
        static_dir=None,
        seed_on_start=False,
    )
    application = create_app(settings)
    lines = [
        ("Waste water is pushing up through the laundry floor drain.", "sewage"),
        ("Está brotando agua residual por el desagüe del lavadero.", "aguas negras"),
        ("Esgoto está saindo pelo ralo da área de serviço agora.", "esgoto"),
        ("Umaapaw ang maruming tubig mula sa lababo ngayon.", "maruming"),
        ("Floor drain se ganda paani bahar aa raha hai.", "gande"),
        ("बाथरूम की नाली से गंदा पानी फैल रहा है।", "गंद"),
        ("باتھ روم کے فرش سے گندا پانی پھیل رہا ہے۔", "گند"),
        ("مياه المجاري تفيض من مصرف الحمام الآن.", "الصرف"),
    ]
    with TestClient(application) as client:
        for line, token in lines:
            started = client.post("/api/demo/calls")
            assert started.status_code == 200
            body = client.post(
                f"/api/demo/calls/{started.json()['id']}/turns",
                json={"text": line},
            ).json()
            say = body["say"]
            lowered = say.lower()
            assert body["outcome"] == "escalated", (line, body["outcome"], say)
            assert "valve" not in lowered and "registro" not in lowered
            assert "what's going on" not in lowered
            assert token in say or token in lowered, (line, say)


def test_howling_equipment_uses_fresh_air_in_the_caller_language():
    lines = [
        "The furnace is screeching in the closet and I cannot catch my breath.",
        "Our boiler will not let up. I feel weak, and the lavatory drips.",
        "El calefactor no deja de chillar y me cuesta respirar, y el grifo gotea.",
        "O aquecedor está urrando e tenho falta de ar, e a pia pinga.",
    ]
    dialog = Dialog(_engine(), None)
    for line in lines:
        state = SessionState()
        heard = dialog.handle(state, line)
        assert state.outcome == "escalated", (line, heard.say)
        blob = heard.say.lower() + heard.say
        assert any(token in blob for token in ("fresh air", "aire libre", "ar livre")), heard.say
        assert "valve" not in heard.say.lower()
        assert "what's going on" not in heard.say.lower()
        if line.startswith("El"):
            assert detect_language(line) == "es"
        if line.startswith("O "):
            assert detect_language(line) == "pt"


def test_portuguese_warm_transfer_without_a_degree():
    dialog = Dialog(_engine(), None)
    for line in (
        "O bebê está gelado e o aquecedor pifou agora.",
        "A idosa está com frio e o aquecimento não esquenta a casa.",
    ):
        assert detect_language(line) == "pt"
        state = SessionState()
        heard = dialog.handle(state, line)
        assert state.outcome == "escalated", heard.say
        assert "aquecido" in heard.say or "fresco" in heard.say
        assert "179" not in heard.say


def test_booking_and_a_weekday_meal_do_not_quote_the_fee():
    engine = _engine()
    booking = "Please book an emergency visit to swap a shower cartridge. It can wait."
    state = SessionState()
    heard = engine.handle(state, booking)
    assert state.outcome != "escalated"
    assert "179" not in heard.say
    for line in ("Thursday at supper still works for me.", "Saturday lunch is open."):
        check = SessionState(phase="hazard_check")
        heard = engine.handle(check, line)
        assert check.outcome != "escalated", line
        assert "179" not in heard.say
