"""Live Claude probe. Not part of pytest, and not a pass-rate score.

Run from the repo root:

    python -m evals.live_claude

Exit 2 when ANTHROPIC_API_KEY is missing. That is the expected result until
someone runs it with a real key. A failed request exits 1 and does not invent
a score. Each dialog turn is capped at the same 8 second budget the phone
loop uses.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# One utterance per call. Hazards are caught before the model speaks.
# The drain line is the one that has to go through Claude.
CALLS = [
    ("gas-odor", "There's a gas odor by the stove and I don't know what to do."),
    ("co-battery", "My CO alarm just needs a new battery."),
    ("drip", "The kitchen faucet has a slow drip. Can I get Friday around noon?"),
    ("discount", "Can you take 20 percent off a drain cleaning?"),
]


def main() -> int:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        print("ANTHROPIC_API_KEY is not set.")
        print("Live Claude has not been measured. No score is reported.")
        return 2

    from app.agent.calendar import MemoryCalendar
    from app.agent.dialog import Dialog
    from app.agent.engine import Engine, SessionState
    from app.config_loader import load_business
    from app.llm.claude import DEFAULT_MODEL, ClaudeClient
    from app.service import FixedClock

    model_name = os.environ.get("ANTHROPIC_MODEL", "").strip() or DEFAULT_MODEL
    client = ClaudeClient(key, model=model_name)
    try:
        probe = client.complete(
            [{"role": "user", "content": "Reply with the single word ready."}],
            tools=[],
            timeout=8,
        )
    except Exception as exc:
        print(f"Claude request failed: {type(exc).__name__}: {exc}")
        print("No live score.")
        return 1
    print(f"model: {model_name}")
    print(f"probe stop_reason: {probe.get('stop_reason')}")

    config = load_business(ROOT / "config" / "business.yaml")
    clock = FixedClock(datetime(2026, 10, 22, 9, 0, tzinfo=ZoneInfo("America/Chicago")))
    engine = Engine(config, MemoryCalendar(), clock)
    dialog = Dialog(engine, client)

    for name, line in CALLS:
        state = SessionState()
        try:
            result = dialog.handle(state, line)
        except Exception as exc:
            print(f"[{name}] error {type(exc).__name__}: {exc}")
            return 1
        print(f"[{name}] outcome={state.outcome} phase={state.phase} latency_ms={result.latency_ms:.0f}")
        print(f"  caller: {line}")
        print(f"  riley: {result.say}")
    print("These four lines are a smoke probe, not the frozen fresh-set score.")
    print("python -m evals.fresh scores the hazard detector without a key.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
