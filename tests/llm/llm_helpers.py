"""Shared fakes for the Q4 model tests (no sockets, no real key)."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

import httpx

from field_quality_agents.llm.budget import BudgetConfig, RetryConfig
from field_quality_agents.llm.client import OpenAIChatClient
from field_quality_agents.llm.credentials import SecretKey
from field_quality_agents.llm.prices import Prices, default_prices

Handler = Callable[[httpx.Request], httpx.Response]

#: Saturday noon UTC: off-peak in the committed price file.
OFF_PEAK = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
#: Wednesday 02:00 UTC: inside the 01:00-04:00 peak window.
PEAK = datetime(2026, 10, 28, 2, 0, tzinfo=UTC)

TOOL = {
    "type": "function",
    "function": {
        "name": "similar_cases",
        "description": "Search similar cases.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}, "k": {"type": "integer"}},
            "required": ["text", "k"],
        },
    },
}


def tool_call(
    *,
    call_id: str = "call_1",
    name: str = "similar_cases",
    arguments: str = '{"text": "intermittent wiper", "k": 5}',
) -> dict[str, object]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


def completion(
    *,
    text: str | None = "",
    calls: Sequence[dict[str, object]] = (),
    finish_reason: str | None = None,
    usage: dict[str, object] | None = None,
) -> dict[str, object]:
    message: dict[str, object] = {"role": "assistant", "content": text}
    if calls:
        message["tool_calls"] = list(calls)
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "deepseek-v4.1-flash",
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason or ("tool_calls" if calls else "stop"),
                "message": message,
            }
        ],
        "usage": usage
        if usage is not None
        else {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    }


def make_client(
    handler: Handler,
    *,
    attempts: int = 3,
    prices: Prices | None = None,
    sleep: Callable[[float], None] | None = None,
    now: Callable[[], datetime] | None = None,
    **kwargs: Any,
) -> OpenAIChatClient:
    sleeps: list[float] = []

    def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    client = OpenAIChatClient(
        transport=httpx.MockTransport(handler),
        api_key=SecretKey("test"),
        prices=prices if prices is not None else default_prices(),
        config=BudgetConfig(retry=RetryConfig(max_attempts=attempts)),
        sleep=sleep if sleep is not None else record_sleep,
        now=now if now is not None else (lambda: OFF_PEAK),
        **kwargs,
    )
    client.recorded_sleeps = sleeps  # type: ignore[attr-defined]
    return client


def json_body(request: httpx.Request) -> dict[str, object]:
    parsed = json.loads(request.content)
    assert isinstance(parsed, dict)
    return parsed
