"""MCP server exposing the DuckDB tool functions over stdio.

The seven tools are exactly the names in ``docs/INTERFACES.md`` §Q2. Each one
is a thin adapter: the business logic lives in :mod:`field_quality_agents.tools`,
so an MCP client and the agent graph cannot drift.

Run it with ``fqa mcp`` or ``python -m field_quality_agents.mcp_server``. The
database comes from ``FQA_DB`` (a fixture file) or ``FQA_DATA_DIR`` (committed
parquet, default ``data``); ``--db`` and ``--data-dir`` override them. While
serving, stdout is the MCP wire: log only to stderr and never print.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import cast

from mcp.server import MCPServer
from pydantic import BaseModel

from field_quality_agents import __version__
from field_quality_agents import tools as tool_api
from field_quality_agents.contracts import Clue, ClueKind

__all__ = ["mcp", "serve"]

_LOGGER = logging.getLogger(__name__)

mcp = MCPServer(
    "field-quality-agents",
    version=__version__,
    instructions="Tools over public NHTSA field-quality data: similar cases, "
    "recalls, investigations, cluster spikes, quote checks, the example "
    "rulebook and case lookup.",
)


def _jsonable(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _as_dicts(value: object) -> list[dict[str, object]]:
    converted = _jsonable(value)
    return cast(list[dict[str, object]], converted)


def _as_dict(value: object) -> dict[str, object]:
    converted = _jsonable(value)
    return cast(dict[str, object], converted)


def _optional_text(raw: dict[str, object], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"filters.{key} must be a string")
    return value


def _optional_year(raw: dict[str, object]) -> int | None:
    value = raw.get("year")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError("filters.year must be an integer")
    return int(value)


def _optional_bool(raw: dict[str, object]) -> bool | None:
    value = raw.get("safety_relevant")
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError("filters.safety_relevant must be a boolean")
    return value


def _parse_filters(raw: dict[str, object] | None) -> tool_api.CaseFilters | None:
    if not raw:
        return None
    allowed = {"make", "model", "year", "group", "safety_relevant"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown filter(s): {', '.join(unknown)}")
    return tool_api.CaseFilters(
        make=_optional_text(raw, "make"),
        model=_optional_text(raw, "model"),
        year=_optional_year(raw),
        group=_optional_text(raw, "group"),
        safety_relevant=_optional_bool(raw),
    )


def _parse_clues(raw: Sequence[dict[str, object]]) -> list[Clue]:
    clues: list[Clue] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each quote must be an object with a quote string")
        quote = item.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            raise ValueError("each quote must have a non-empty quote string")
        kind_value = str(item.get("kind", ClueKind.OTHER.value))
        try:
            kind = ClueKind(kind_value)
        except ValueError:
            kind = ClueKind.OTHER
        clues.append(Clue(kind=kind, quote=quote))
    return clues


@mcp.tool()
def similar_cases(
    text: str,
    filters: dict[str, object] | None = None,
    k: int = 10,
) -> list[dict[str, object]]:
    """Find similar complaints with BM25; scores are rounded and ties go by id."""

    return _as_dicts(tool_api.similar_cases(text, _parse_filters(filters), k))


@mcp.tool()
def recalls_for(make: str, model: str, year: int, group: str) -> list[dict[str, object]]:
    """Return recalls for one make, model, year and component group."""

    return _as_dicts(tool_api.recalls_for(make, model, year, group))


@mcp.tool()
def investigations_for(
    make: str,
    model: str,
    year: int,
    group: str,
) -> list[dict[str, object]]:
    """Return investigations for one make, model, year and component group."""

    return _as_dicts(tool_api.investigations_for(make, model, year, group))


@mcp.tool()
def cluster_stats(
    make: str,
    model: str,
    year: int,
    group: str,
    until_date: str,
) -> dict[str, object]:
    """Weekly cluster counts and the Poisson 99.9% spike state up to a date."""

    return _as_dict(
        tool_api.cluster_stats(make, model, year, group, date.fromisoformat(until_date))
    )


@mcp.tool()
def verify_quotes(text: str, quotes: list[dict[str, object]]) -> list[dict[str, object]]:
    """Check quotes as verbatim spans after whitespace normalisation."""

    return _as_dicts(tool_api.verify_quotes(text, _parse_clues(quotes)))


@mcp.tool()
def rulebook(conditions: list[str]) -> list[dict[str, object]]:
    """Map reported conditions to targeted tests from the example rulebook."""

    return _as_dicts(tool_api.rulebook(conditions))


@mcp.tool()
def case_lookup(id: str) -> dict[str, object] | None:
    """Return one case by id, or null when it is not in the knowledge base."""

    case = tool_api.case_lookup(id)
    return None if case is None else _as_dict(case)


def serve(
    *,
    data_dir: str | Path | None = None,
    db_path: str | Path | None = None,
    rulebook_path: str | Path | None = None,
) -> int:
    """Configure the toolbox and serve MCP over stdio until the client closes."""

    tool_api.configure(data_dir=data_dir, db_path=db_path, rulebook_path=rulebook_path)
    _LOGGER.info("serving field-quality-agents MCP tools over stdio")
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(serve())
