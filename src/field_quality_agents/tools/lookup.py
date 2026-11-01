"""Exact lookups for recalls, investigations and one case."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from field_quality_agents.contracts import Case
from field_quality_agents.tools.db import Toolbox

__all__ = ["case_lookup", "investigations_for", "recalls_for"]

_EVENT_COLUMNS = "id, make, model, year, component, \"group\", summary, open_date"


def _iso_date(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _events_for(
    toolbox: Toolbox,
    table: str,
    make: str,
    model: str,
    year: int,
    group: str,
) -> list[dict[str, object]]:
    rows: list[tuple[Any, ...]] = toolbox.connection.execute(
        f"""
        SELECT {_EVENT_COLUMNS}
        FROM {table}
        WHERE upper(make) = upper(?)
          AND upper(model) = upper(?)
          AND year = ?
          AND "group" = ?
        ORDER BY open_date DESC NULLS LAST, id ASC
        """,
        [make, model, year, group],
    ).fetchall()
    return [
        {
            "id": str(row[0]),
            "make": str(row[1]),
            "model": str(row[2]),
            "year": int(row[3]),
            "component": str(row[4] or ""),
            "group": str(row[5] or ""),
            "summary": str(row[6] or ""),
            "open_date": _iso_date(row[7]),
        }
        for row in rows
    ]


def recalls_for(
    toolbox: Toolbox,
    make: str,
    model: str,
    year: int,
    group: str,
) -> list[dict[str, object]]:
    """Recalls for one vehicle key, newest open date first, then id."""

    return _events_for(toolbox, "recalls", make, model, year, group)


def investigations_for(
    toolbox: Toolbox,
    make: str,
    model: str,
    year: int,
    group: str,
) -> list[dict[str, object]]:
    """Investigations for one vehicle key, newest open date first, then id."""

    return _events_for(toolbox, "investigations", make, model, year, group)


def case_lookup(toolbox: Toolbox, id: str) -> Case | None:
    """Return one case from the knowledge base or replay set."""

    row = toolbox.connection.execute(
        """
        SELECT id, received_at, make, model, year, component, narrative,
               "group", safety_relevant, mileage
        FROM cases
        WHERE id = ?
        LIMIT 1
        """,
        [id],
    ).fetchone()
    if row is None:
        return None
    received_at = row[1]
    if isinstance(received_at, datetime):
        received_at = received_at.date()
    elif not isinstance(received_at, date):
        received_at = date.fromisoformat(str(received_at))
    return Case(
        id=str(row[0]),
        received_at=received_at,
        make=str(row[2]),
        model=str(row[3]),
        year=int(row[4]),
        component=str(row[5]),
        narrative=str(row[6] or ""),
        group=str(row[7]) if row[7] is not None else None,
        safety_relevant=bool(row[8]),
        source_id=str(row[0]),
        mileage=int(row[9]) if row[9] is not None else None,
    )
