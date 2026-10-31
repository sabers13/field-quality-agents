"""Transport-independent model result shapes and recording helpers.

These are the frozen shapes from ``docs/INTERFACES.md`` §Q4. Everything the
client, the recorder and the LangChain adapter exchange is one of these
dataclasses, so recordings never depend on httpx or LangChain internals.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, cast

__all__ = [
    "ChatResponse",
    "ToolCall",
    "Usage",
    "response_from_dict",
    "response_to_dict",
]


@dataclass(frozen=True)
class ToolCall:
    """One function call the model asked for; arguments are already parsed."""

    id: str
    name: str
    arguments: dict[str, object]


@dataclass(frozen=True)
class Usage:
    """Token counts and the cost fields reported by the endpoint."""

    input_tokens: int
    output_tokens: int
    reasoning_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: float | None = None
    list_cost_usd: float | None = None
    allowance_usd: float | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class ChatResponse:
    """One completed chat turn, ready to be recorded and replayed."""

    text: str
    tool_calls: tuple[ToolCall, ...]
    finish_reason: str
    usage: Usage
    raw: dict[str, object] = field(default_factory=dict)
    latency_ms: int = 0

    @property
    def policy_text(self) -> str:
        """Text scanned for abuse/policy warnings, without dumping the whole body."""

        return "\n".join(part for part in (self.text, _error_text(self.raw)) if part)


def _error_text(raw: Mapping[str, object]) -> str:
    error = raw.get("error")
    if isinstance(error, str):
        return error
    if isinstance(error, Mapping):
        message = error.get("message")
        return message if isinstance(message, str) else ""
    return ""


def response_to_dict(response: ChatResponse) -> dict[str, object]:
    """Serialise a response into a JSON-compatible recording body."""

    return {
        "text": response.text,
        "tool_calls": [
            {"id": call.id, "name": call.name, "arguments": call.arguments}
            for call in response.tool_calls
        ],
        "finish_reason": response.finish_reason,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "reasoning_tokens": response.usage.reasoning_tokens,
            "cached_tokens": response.usage.cached_tokens,
            "cost_usd": response.usage.cost_usd,
            "list_cost_usd": response.usage.list_cost_usd,
            "allowance_usd": response.usage.allowance_usd,
        },
        "raw": response.raw,
        "latency_ms": response.latency_ms,
    }


def response_from_dict(payload: Mapping[str, object]) -> ChatResponse:
    """Read a recording body; a malformed recording is not silently repaired."""

    tool_calls_raw = payload.get("tool_calls", [])
    tool_calls: list[ToolCall] = []
    if isinstance(tool_calls_raw, list):
        for item in tool_calls_raw:
            if not isinstance(item, Mapping):
                raise ValueError("recording tool_calls entry is not an object")
            arguments = item.get("arguments", {})
            if not isinstance(arguments, Mapping):
                raise ValueError("recording tool call arguments are not an object")
            tool_calls.append(
                ToolCall(
                    id=_string(item.get("id"), "tool call id"),
                    name=_string(item.get("name"), "tool call name"),
                    arguments={str(key): value for key, value in arguments.items()},
                )
            )

    usage_raw = payload.get("usage", {})
    if not isinstance(usage_raw, Mapping):
        raise ValueError("recording usage is not an object")
    usage = Usage(
        input_tokens=_int(usage_raw.get("input_tokens"), "input_tokens"),
        output_tokens=_int(usage_raw.get("output_tokens"), "output_tokens"),
        reasoning_tokens=_int(usage_raw.get("reasoning_tokens", 0), "reasoning_tokens"),
        cached_tokens=_int(usage_raw.get("cached_tokens", 0), "cached_tokens"),
        cost_usd=_float_or_none(usage_raw.get("cost_usd")),
        list_cost_usd=_float_or_none(usage_raw.get("list_cost_usd")),
        allowance_usd=_float_or_none(usage_raw.get("allowance_usd")),
    )

    raw = payload.get("raw", {})
    if not isinstance(raw, Mapping):
        raw = {}

    return ChatResponse(
        text=_string(payload.get("text", ""), "text"),
        tool_calls=tuple(tool_calls),
        finish_reason=_string(payload.get("finish_reason"), "finish_reason"),
        usage=usage,
        raw=cast(dict[str, object], dict(raw)),
        latency_ms=_int(payload.get("latency_ms", 0), "latency_ms"),
    )


def _string(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"recording {name} is not a string")
    return value


def _int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"recording {name} is not an integer")
    return value


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("recording cost is not a number")
    return float(value)


def json_object(value: object) -> dict[str, object]:
    """Narrow arbitrary JSON to an object without lying about its shape."""

    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return cast(dict[str, object], value)


def as_mapping(value: object) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return cast(Mapping[str, Any], value)
    return None
