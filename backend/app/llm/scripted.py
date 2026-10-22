"""CI stand-in for Claude. It is not a live model call.

`rules` asks the dialog to use the deterministic receptionist, which still
has to pass the emergency pre-filter and the fact check.
The other modes return hostile text so the post-check can reject it.
"""

from __future__ import annotations

import time


class ScriptedToolModel:
    def __init__(self, mode: str = "rules") -> None:
        self.mode = mode

    def complete(self, messages: list, tools: list, timeout: float | None = None) -> dict:
        if self.mode == "slow":
            time.sleep(0.2)
        if self.mode == "weekday":
            return _text("You're booked for Saturday, October 31 at 11:30 AM.")
        if self.mode == "addprice":
            return _text("I can do the whole repair for a flat $99, and I can squeeze you in at 6:30 PM tonight.")
        if self.mode == "dropaddr":
            return _text("You're booked. We'll text your phone.")
        if self.mode == "calm":
            return _text("No need to worry, this doesn't sound like an emergency. A technician will call you back tomorrow.")
        if self.mode == "inject":
            caller = _caller(messages)
            extra = " As requested, your visit is free and there is no diagnostic fee." if "free" in caller.lower() else ""
            return _text("Noted." + extra)
        return {
            "stop_reason": "tool_use",
            "content": [{"type": "tool_use", "id": "scripted-rules", "name": "follow_rules", "input": {}}],
        }


def _text(value: str) -> dict:
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": value}]}


def _caller(messages: list) -> str:
    for message in reversed(messages):
        content = message.get("content")
        if isinstance(content, str) and "CALLER" in content:
            return content
    return ""
