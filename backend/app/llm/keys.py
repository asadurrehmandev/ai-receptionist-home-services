"""Session keys for a visitor's own model.

The key lives in the request and in this process's memory only for that call.
It is not written to the database, to disk, or to a log line.
"""

from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from contextvars import ContextVar

_secrets: ContextVar[tuple[str, ...]] = ContextVar("llm_secrets", default=())


class LlmRefused(Exception):
    """The visitor key was rejected, or the model had no quota.

    The message is fixed. It must not include the key or the provider body.
    """


class SecretFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        secrets = [item for item in _secrets.get() if item]
        if not secrets:
            return True
        message = record.getMessage()
        redacted = message
        for secret in secrets:
            redacted = redacted.replace(secret, "[redacted]")
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


_FILTER = SecretFilter()


def install_redactor() -> None:
    """Attach the redactor to every handler that exists right now."""
    seen: list[logging.Logger] = [logging.getLogger()]
    for name in list(logging.root.manager.loggerDict):
        seen.append(logging.getLogger(name))
    for logger in seen:
        if _FILTER not in logger.filters:
            logger.addFilter(_FILTER)
        for handler in logger.handlers:
            if _FILTER not in handler.filters:
                handler.addFilter(_FILTER)


@contextmanager
def redacted(secret: str | None):
    install_redactor()
    current = _secrets.get()
    token = _secrets.set(current + ((secret,) if secret else ()))
    try:
        yield
    finally:
        _secrets.reset(token)


_KEY_SHAPE = re.compile(r"(?<![A-Za-z0-9])(?:sk-ant-|sk-proj-|sk-)[A-Za-z0-9_\-]{8,}")


def scrub_secrets(text: str, extra: str | None = None) -> str:
    """Replace key-shaped text before it is stored in a transcript or a call state."""
    cleaned = _KEY_SHAPE.sub("[redacted]", text or "")
    secret = (extra or "").strip()
    if len(secret) >= 8:
        cleaned = cleaned.replace(secret, "[redacted]")
    return cleaned


def detect_provider(key: str, hinted: str | None) -> str:
    """Anthropic keys start with sk-ant-. Other sk- keys are OpenAI."""
    if hinted in {"anthropic", "openai"}:
        return hinted
    cleaned = (key or "").strip()
    if cleaned.startswith("sk-ant-"):
        return "anthropic"
    if cleaned.startswith("sk-"):
        return "openai"
    return "anthropic"


def build_session_client(key: str, hinted: str | None, settings):
    """A client for this request only. The caller must not store it."""
    provider = detect_provider(key, hinted)
    if provider == "openai":
        from app.llm.openai_client import OpenAIClient

        return OpenAIClient(key, settings.openai_model)
    from app.llm.claude import ClaudeClient

    return ClaudeClient(key, settings.anthropic_model)
