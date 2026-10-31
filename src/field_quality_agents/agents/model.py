"""The model seam for the desk.

Q4 owns the real LangChain-compatible chat model. Until it lands the graph
depends on this small protocol only, so tests can drive every branch with a
scripted fake and Q4's adapter can implement ``complete`` without touching the
agents.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from field_quality_agents.contracts import Clue, ClueKind


@dataclass(frozen=True)
class ModelTurn:
    """One model answer: text, the tokens it used and its cost."""

    text: str
    tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0


class AgentModel(Protocol):
    """A chat model that answers one agent turn at a time."""

    def complete(
        self,
        *,
        agent: str,
        prompt_version: str,
        prompt: str,
        messages: Sequence[Mapping[str, object]],
        tools: Sequence[Mapping[str, object]] = (),
    ) -> ModelTurn: ...


class ModelOutputError(ValueError):
    """The model answered, but not with a readable JSON object."""


def parse_json_object(text: str) -> dict[str, object]:
    """Return the first JSON object in ``text``; tolerate code fences and prose."""

    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            candidate = "\n".join(lines[1:-1]).strip()
        if candidate.startswith("json"):
            candidate = candidate[4:].strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        parsed = _scan_for_object(candidate)
    if not isinstance(parsed, dict):
        raise ModelOutputError("model output is not a JSON object")
    return parsed


def _scan_for_object(text: str) -> object:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            parsed, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        return parsed
    raise ModelOutputError("model output has no JSON object")


def as_text(payload: Mapping[str, object], key: str, default: str = "") -> str:
    value = payload.get(key, default)
    return value.strip() if isinstance(value, str) else default


def as_bool(payload: Mapping[str, object], key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    return value if isinstance(value, bool) else default


def as_text_list(payload: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list):
        return ()
    items = (item.strip() for item in value if isinstance(item, str))
    return tuple(item for item in items if item)


def as_clues(payload: Mapping[str, object], key: str = "clues") -> tuple[Clue, ...]:
    """Read the model's clue list; unknown kinds fall back to ``other``."""

    raw = payload.get(key)
    if not isinstance(raw, list):
        return ()
    clues: list[Clue] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        quote = item.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            continue
        kind_text = item.get("kind")
        try:
            kind = ClueKind(kind_text) if isinstance(kind_text, str) else ClueKind.OTHER
        except ValueError:
            kind = ClueKind.OTHER
        clues.append(Clue(kind=kind, quote=quote.strip()))
    return tuple(clues)
