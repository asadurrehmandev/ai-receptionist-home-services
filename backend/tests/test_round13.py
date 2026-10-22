"""Round 13 classes: head recall, composition, slots, and the unclear path.

The held-out file was hashed before training. Do not edit its lines to lift a score.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.agent.calendar import MemoryCalendar
from app.agent.engine import Engine, SessionState
from app.agent.hazard import classify_emergency
from app.agent.hazard_head import decide, hazard_probs, head_level
from app.agent.nlu import extract_street, fallback_name, guess_bare_name
from app.config_loader import load_business
from app.service import FixedClock
from evals.round13_heldout_set import HELDOUT

ROOT = Path(__file__).resolve().parents[2]
THU = datetime(2026, 10, 22, 9, 0, tzinfo=ZoneInfo("America/Chicago"))
CONFIG = load_business(ROOT / "config" / "business.yaml")
HELDOUT_SHA = "85f1015ac4f77a31638016a40de7360591e4c4feb6be50f16bd558e2b49549e1"


def _engine() -> Engine:
    return Engine(CONFIG, MemoryCalendar(), FixedClock(THU))


def test_round13_heldout_file_is_unchanged():
    digest = hashlib.sha256((ROOT / "evals" / "round13_heldout_set.py").read_bytes()).hexdigest()
    assert digest == HELDOUT_SHA
    assert len(HELDOUT) >= 120


def test_head_only_heldout_recall_is_at_least_90_percent():
    emergencies = [row for row in HELDOUT if row[0] == "emergency"]
    hits = 0
    by_family: dict[str, list[bool]] = {}
    by_language: dict[str, list[bool]] = {}
    false_pages = 0
    non_emergency = 0
    for label, family, language, text in HELDOUT:
        probs = hazard_probs(text)
        assert probs is not None, text
        decision = decide(probs)
        if label == "emergency":
            hit = decision == "emergency"
            hits += int(hit)
            by_family.setdefault(family, []).append(hit)
            by_language.setdefault(language, []).append(hit)
        else:
            non_emergency += 1
            if decision == "emergency":
                false_pages += 1
    recall = hits / len(emergencies)
    assert recall >= 0.90, (hits, len(emergencies), by_family, by_language)
    assert false_pages / non_emergency <= 0.02
    for family, flags in by_family.items():
        assert flags, family
    for language, flags in by_language.items():
        assert sum(flags) / len(flags) >= 0.70, (language, sum(flags), len(flags))


def test_composition_pages_comfort_and_co_and_keeps_a_chirp():
    heat, _ = classify_emergency("the heat just quit and its 44 inside, my dad is 88")
    assert heat == "definite"
    roman, _ = classify_emergency("Heater band hai, dadi 84 saal ki hain aur andar bahut thand hai")
    assert roman == "definite"
    short_gas, _ = classify_emergency("gas ki boo aa rahi hai")
    assert short_gas == "definite"
    burst, _ = classify_emergency("pani ka pipe phat gaya hai")
    assert burst == "definite"
    sparks, _ = classify_emergency("bathroom socket se chingariyan nikal rahi hain")
    assert sparks == "definite"
    service, _ = classify_emergency("Gas fireplace ki servicing chahiye, koi boo nahi hai.")
    assert service != "definite"
    alarm, _ = classify_emergency("the co alarm is going and my head is pounding")
    assert alarm == "definite"
    chirp, why = classify_emergency("The nursery CO detector chirped a couple of times. I think the battery is low.")
    assert chirp == "advice", why
    keeps, _ = classify_emergency("my CO alarm keeps chirping")
    assert keeps == "definite"
    flicker, _ = classify_emergency("The lights keep flickering whenever the pantry toaster runs.")
    assert flicker == "ask"
    lamp, _ = classify_emergency("No smoke and no sparks. The pantry lamp just flickers.")
    assert lamp == "none"


def test_multipart_names_keep_particles_and_intent_phrases_do_not():
    assert guess_bare_name("Muhammad Asad ur Rehman", framed=True) == "Muhammad Asad ur Rehman"
    assert guess_bare_name("Helena van der Meer", framed=True) == "Helena van der Meer"
    assert guess_bare_name("Ali bin Yusuf", framed=True) == "Ali bin Yusuf"
    assert guess_bare_name("Sí Quiero Agendar", framed=True) is None
    assert guess_bare_name("yes I want to book", framed=True) is None
    assert guess_bare_name("it's due for maintenance", framed=True) is None
    assert fallback_name("????") == "Caller"
    engine = _engine()
    state = SessionState(phase="quote_decision", intent="quote", issue="Water heater", quote_given=True)
    engine.handle(state, "si, quiero agendar")
    assert state.name is None


def test_spanish_address_accepts_number_last_and_then_stops_asking():
    assert "Lamar" in (extract_street("calle Lamar 2200", answering=True) or "")
    assert "2200" in (extract_street("calle Lamar 2200", answering=True) or "")
    assert "2200" in (extract_street("Lamar Street 2200", answering=True) or "")
    engine = _engine()
    state = SessionState(
        phase="collect_address",
        language="es",
        intent="new_job",
        issue="Faucet",
        name="Rosa Diaz",
        phone="5125550199",
    )
    heard = engine.handle(state, "calle Rio 18")
    assert state.street and "Rio" in state.street and "18" in state.street
    assert "necesito la calle" not in heard.say.lower()
    stuck = SessionState(
        phase="collect_address",
        language="es",
        intent="new_job",
        issue="Faucet",
        name="Rosa Diaz",
        phone="5125550199",
    )
    last = None
    for _ in range(3):
        last = engine.handle(stuck, "no se")
    assert stuck.outcome == "callback"
    assert stuck.phase == "closed"
    assert last is not None and "oficina" in last.say.lower()


def test_two_failed_issue_turns_ask_safety_then_a_separate_callback():
    engine = _engine()
    state = SessionState(phase="collect_issue", intent="new_job")
    first = engine.handle(state, "hmm")
    assert state.phase == "collect_issue"
    assert "more" in first.say.lower() or "más" in first.say.lower() or "mas" in first.say.lower()
    second = engine.handle(state, "hmm")
    assert state.phase == "unclear_handoff"
    assert "danger" in second.say.lower() or "peligro" in second.say.lower()
    offered = engine.handle(state, "no")
    assert state.outcome != "escalated"
    assert state.phase == "callback_offer"
    assert "call you back" in offered.say.lower() or "devuelva" in offered.say.lower()
    booked = engine.handle(state, "yes")
    assert state.outcome == "callback"
    assert state.hazard is None


def test_a_heldout_hazard_still_pages_end_to_end():
    engine = _engine()
    for label, family, language, text in HELDOUT:
        if label != "emergency":
            continue
        if family not in {"gas", "electrical", "comfort"} or language not in {"en", "roman", "hi"}:
            continue
        level, _why = classify_emergency(text)
        assert level == "definite", (family, language, text, level)
        own = head_level(text)
        assert own is not None and own[0] == "definite", (family, language, text, own)
        state = SessionState()
        heard = engine.handle(state, text)
        assert state.outcome == "escalated", (family, language, text, heard.say)
        break
    else:
        raise AssertionError("no sample")
