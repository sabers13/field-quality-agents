"""The tool seam for the desk.

These types mirror ``docs/INTERFACES.md`` §Q2. Q2 owns the real DuckDB tools;
Q5 injects an object that satisfies ``ToolRegistry`` so the graph can run on
fakes today and on Q2's typed functions once they land (Q8 wires the adapter).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, is_dataclass
from typing import Protocol, runtime_checkable

from field_quality_agents.contracts import Clue


@dataclass(frozen=True)
class CaseFilters:
    make: str | None = None
    model: str | None = None
    year: int | None = None
    group: str | None = None
    safety_relevant: bool | None = None


@dataclass(frozen=True)
class SimilarCase:
    id: str
    score: float
    make: str
    model: str
    year: int
    group: str
    excerpt: str


@dataclass(frozen=True)
class QuoteVerification:
    quote: str
    verified: bool


@runtime_checkable
class ToolRegistry(Protocol):
    """The subset of Q2 tools the case graph calls."""

    def similar_cases(
        self,
        text: str,
        filters: CaseFilters | None = None,
        k: int = 10,
    ) -> list[SimilarCase]: ...

    def recalls_for(
        self, make: str, model: str, year: int, group: str
    ) -> list[dict[str, object]]: ...

    def investigations_for(
        self, make: str, model: str, year: int, group: str
    ) -> list[dict[str, object]]: ...

    def rulebook(self, conditions: Sequence[str]) -> list[dict[str, object]]: ...

    def verify_quotes(self, text: str, quotes: Sequence[Clue]) -> list[QuoteVerification]: ...


def to_jsonable(value: object) -> object:
    """Turn tool results into plain data for a ``TraceStep.tool_output``."""

    if is_dataclass(value) and not isinstance(value, type):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def tool_output(payload: object) -> dict[str, object]:
    """Wrap a tool result as the mapping a trace step accepts."""

    converted = to_jsonable(payload)
    return converted if isinstance(converted, dict) else {"result": converted}
