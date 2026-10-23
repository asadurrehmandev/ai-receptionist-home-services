"""Round 21: a drip, a fixture, or a tub does not explain a definite head.

When the present-hazard lists miss, that match must not zero the head.
The caller is paged or asked the safety question. Sewage stays away from
the water valve. A rotten-egg odor, including a hyphen, leaves the house.
A weekday and a meal answered to the safety question is not a yes.
The held-out file was hashed before this round's policy edit. Do not edit
its lines to lift a score. Do not move the page cut.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.agent.calendar import MemoryCalendar
from app.agent.engine import Engine, SessionState
from app.agent.hazard import classify_emergency
from app.agent.nlu import detect_language, extract_issue
from app.config_loader import load_business
from app.service import FixedClock
from evals.round21_heldout_set import HELDOUT

ROOT = Path(__file__).resolve().parents[2]
THU = datetime(2026, 10, 22, 9, 0, tzinfo=ZoneInfo("America/Chicago"))
CONFIG = load_business(ROOT / "config" / "business.yaml")
HELDOUT_SHA = "b89c9a8673a91c4d0fc28bc91689f2aab6e3ab920e3ff516a5da8b407fc8e559"


def _engine() -> Engine:
    return Engine(CONFIG, MemoryCalendar(), FixedClock(THU))


def test_round21_heldout_file_is_unchanged():
    digest = hashlib.sha256((ROOT / "evals" / "round21_heldout_set.py").read_bytes()).hexdigest()
    assert digest == HELDOUT_SHA
    assert len(HELDOUT) >= 40


def test_page_cut_stays_put_and_the_source_default_matches_it():
    source = (ROOT / "backend" / "app" / "agent" / "hazard_head.py").read_text()
    assert "PAGE_MIN = 0.55" in source
    assert "PAGE_MIN = 0.80" not in source
    from app.agent import hazard_head

    hazard_head._weights()
    assert round(hazard_head.PAGE_MIN, 2) == 0.55
    assert round(hazard_head.ASK_MIN, 2) == 0.55
    assert round(hazard_head.PAGE_MARGIN, 2) == 0.02
    assert round(hazard_head.ROUTINE_LOCK, 2) == 0.40


def test_a_tub_drip_does_not_zero_a_definite_head(monkeypatch):
    monkeypatch.setattr("app.agent.hazard_head.head_level", lambda text: ("definite", "Hazard"))
    monkeypatch.setattr("app.agent.hazard._emergency_probability", lambda text: 0.84)
    line = "The tub has a slow drip and there is a smell I cannot place."
    level, label = classify_emergency(line)
    assert level in {"definite", "ask"}, (level, label)
    state = SessionState()
    heard = _engine().handle(state, line)
    assert state.phase != "collect_name"
    assert state.outcome == "escalated" or state.phase == "hazard_check"
    assert "name" not in heard.say.lower()
    assert "what's going on" not in heard.say.lower()


def test_howling_with_a_tub_drip_uses_fresh_air():
    lines = [
        "The mechanical closet is shrieking, I feel nauseated, and the tub has a slow drip.",
        "The air handler will not stop wailing. My head is pounding and the lavatory drips.",
        "El equipo del ático aúlla, estoy mareada, y la tina gotea.",
        "O exaustor está guinchando, estou tonta, e a banheira pinga.",
    ]
    for line in lines:
        assert detect_language(line) != "en" or line.startswith("The")
        level, label = classify_emergency(line)
        assert level == "definite", (line, level, label)
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome == "escalated", line
        lowered = heard.say.lower()
        assert "what's going on" not in lowered
        assert any(token in lowered or token in heard.say for token in ("fresh air", "aire libre", "ar livre"))
        assert "valve" not in lowered


def test_water_off_a_ceiling_fan_stays_electrical_with_a_room_in_between():
    line = "Water is running off the upstairs guest bedroom ceiling fan."
    level, label = classify_emergency(line)
    assert level == "definite", (level, label)
    assert label == "Electrical hazard"
    state = SessionState()
    heard = _engine().handle(state, line)
    lowered = heard.say.lower()
    assert "stay away" in lowered
    assert "valve" not in lowered
    assert state.phase != "collect_name"


def test_sewage_uses_stay_away_and_rotten_egg_leaves_the_house():
    sewage = [
        "Gray water keeps belching out of the tub and it smells like a sewer.",
        "Sale agua fétida del desagüe de la ducha y no para.",
        "Água fedida está voltando pelo ralo do banheiro.",
    ]
    for line in sewage:
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome == "escalated", line
        lowered = heard.say.lower()
        assert "valve" not in lowered and "registro" not in lowered
        assert "what's going on" not in lowered
        assert any(
            token in lowered or token in heard.say
            for token in ("sewage", "aguas negras", "esgoto")
        )
    gas_lines = [
        ("There is a rotten-egg smell at the meter and I feel dizzy.", "smell gas"),
        ("A rotten-egg odor is hanging by the furnace flue.", "smell gas"),
        ("हवा में सड़े अंडे की गंध है और चक्कर आ रहे हैं।", "गंध"),
        ("ہوا میں سڑے انڈے کی بو ہے اور چکر آ رہے ہیں۔", "بو"),
        ("رائحة بيض فاسد عند العداد وأشعر بالدوار.", "غاز"),
    ]
    for line, token in gas_lines:
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome == "escalated", line
        assert token in heard.say or token in heard.say.lower()
        assert "what's going on" not in heard.say.lower()


def test_romance_howl_and_spark_are_not_heard_as_english():
    lines = {
        "Hay chispas saltando del enchufe del lavadero ahora mismo.": "es",
        "El equipo del ático aúlla, estoy mareada, y la tina gotea.": "es",
        "A tomada da lavanderia está soltando faíscas neste momento.": "pt",
        "O exaustor está guinchando, estou tonta, e a banheira pinga.": "pt",
    }
    for line, language in lines.items():
        assert detect_language(line) == language
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.language == language
        assert "what's going on" not in heard.say.lower()


def test_a_weekday_and_a_meal_answered_to_safety_is_not_a_yes():
    engine = _engine()
    for line in ("Wednesday at dinner still works.", "Friday breakfast is fine.", "Tuesday dinner"):
        state = SessionState(phase="hazard_check")
        heard = engine.handle(state, line)
        assert state.outcome != "escalated", line
        lowered = heard.say.lower()
        assert "179" not in lowered
        assert "emergency dispatch" not in lowered


def test_a_slow_drain_is_kept_as_the_issue():
    assert extract_issue("The basin takes a long time to empty after a shower.") == "Clogged drain"
    state = SessionState(phase="collect_issue", intent="new_job")
    heard = _engine().handle(state, "The basin takes a long time to empty after a shower.")
    assert state.issue
    assert state.outcome != "callback"
    assert state.outcome != "escalated"
    lowered = heard.say.lower()
    assert "179" not in lowered
    assert "call you back" not in lowered


def test_booking_disposal_and_ice_maker_still_do_not_page():
    lines = [
        "Please book an emergency visit to replace the powder-room aerator.",
        "My garbage disposal is jammed.",
        "The ice maker is overflowing into the freezer.",
    ]
    for line in lines:
        level, label = classify_emergency(line)
        assert level != "definite", (line, level, label)
        state = SessionState()
        heard = _engine().handle(state, line)
        assert state.outcome != "escalated", line
        assert "179" not in heard.say.lower()
        assert "emergency dispatch" not in heard.say.lower()
