"""OpenAI tool-calling client with the same shape as ClaudeClient.

The dialog speaks Anthropic content blocks. This client translates them and
translates the reply back. The key is sent as a header and is not logged.
"""

from __future__ import annotations

import json

import httpx

from app.llm.claude import SYSTEM
from app.llm.keys import LlmRefused

DEFAULT_MODEL = "gpt-4.1"
API_URL = "https://api.openai.com/v1/chat/completions"
CALL_TIMEOUT = 5.0


class OpenAIClient:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, client: httpx.Client | None = None) -> None:
        self.api_key = api_key
        self.model = model or DEFAULT_MODEL
        self.provider = "openai"
        self._client = client

    def complete(self, messages: list, tools: list, timeout: float | None = None) -> dict:
        own = self._client is None
        client = self._client or httpx.Client(timeout=timeout or CALL_TIMEOUT)
        try:
            response = client.post(
                API_URL,
                headers={
                    "authorization": f"Bearer {self.api_key}",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 800,
                    "messages": _to_openai(messages),
                    "tools": _tools(tools),
                },
            )
            if response.status_code in {401, 403, 429, 402}:
                raise LlmRefused("The key was refused or has no quota.")
            response.raise_for_status()
            body = response.json()
        except LlmRefused:
            raise
        except httpx.HTTPError:
            raise LlmRefused("The model could not be called.") from None
        finally:
            if own:
                client.close()
        return _from_openai(body)


def _tools(tools: list) -> list:
    converted = []
    for tool in tools:
        schema = tool.get("input_schema")
        if schema is None:
            converted.append(tool)
            continue
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description") or "",
                    "parameters": schema,
                },
            }
        )
    return converted


def _to_openai(messages: list) -> list:
    out: list[dict] = [{"role": "system", "content": SYSTEM}]
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if role == "assistant" and isinstance(content, list):
            tool_calls = []
            texts = []
            for block in content:
                if block.get("type") == "tool_use":
                    tool_calls.append(
                        {
                            "id": block.get("id") or "tool",
                            "type": "function",
                            "function": {
                                "name": block.get("name") or "",
                                "arguments": json.dumps(block.get("input") or {}),
                            },
                        }
                    )
                elif block.get("type") == "text" and block.get("text"):
                    texts.append(block["text"])
            item: dict = {"role": "assistant", "content": "\n".join(texts) or ""}
            if tool_calls:
                item["tool_calls"] = tool_calls
            out.append(item)
            continue
        if role == "user" and isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_result":
                    out.append(
                        {
                            "role": "tool",
                            "tool_call_id": block.get("tool_use_id") or "tool",
                            "content": block.get("content") or "",
                        }
                    )
            continue
        out.append({"role": role or "user", "content": content if isinstance(content, str) else json.dumps(content)})
    return out


def _from_openai(body: dict) -> dict:
    choices = body.get("choices") or []
    message = (choices[0].get("message") if choices else None) or {}
    content = []
    if message.get("content"):
        content.append({"type": "text", "text": message["content"]})
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        raw = function.get("arguments") or "{}"
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        content.append(
            {
                "type": "tool_use",
                "id": call.get("id") or "tool",
                "name": function.get("name") or "",
                "input": payload,
            }
        )
    stop = "tool_use" if message.get("tool_calls") else "end_turn"
    return {"stop_reason": stop, "content": content}
