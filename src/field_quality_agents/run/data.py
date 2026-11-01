"""Input data for a run: cases, ground-truth events and a tool connection.

A real run reads the committed parquet files. ``make all`` and the end-to-end
tests use a small fixture DuckDB built from SQL so no model call and no live
download is needed. Both paths expose the same shapes to the pipeline.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, cast

import duckdb

from field_quality_agents.contracts import Case
from field_quality_agents.metrics.issues import Event
from field_quality_agents.tools.db import Toolbox

__all__ = ["RunSource", "open_source"]

_CASE_COLUMNS = (
    "id, received_at, make, model, year, component, narrative, "
    '"group" AS group_name, safety_relevant, mileage'
)


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _case_from_row(row: tuple[Any, ...]) -> Case:
    (
        case_id,
        received_at,
        make,
        model,
        year,
        component,
        narrative,
        group_name,
        safety_relevant,
        mileage,
    ) = row
    return Case(
        id=str(case_id),
        received_at=_as_date(received_at),
        make=str(make),
        model=str(model),
        year=int(year),
        component=str(component),
        narrative=str(narrative or ""),
        group=str(group_name) if group_name is not None else None,
        safety_relevant=bool(safety_relevant),
        source_id=str(case_id),
        mileage=int(mileage) if mileage is not None else None,
    )


@dataclass
class RunSource:
    """One open data source: a fixture DuckDB or the committed parquet files."""

    toolbox: Toolbox
    data_dir: Path | None = None
    db_path: Path | None = None
    temp_dir: tempfile.TemporaryDirectory[str] | None = None

    def cases(self) -> list[Case]:
        if self.db_path is not None:
            rows = self.toolbox.connection.execute(
                f"SELECT {_CASE_COLUMNS} FROM cases ORDER BY received_at, id"
            ).fetchall()
        else:
            if self.data_dir is None:
                raise RuntimeError("a run source needs a data directory or a fixture DB")
            path = self.data_dir / "replay_2025.parquet"
            if not path.is_file():
                raise FileNotFoundError(f"missing replay set: {path}")
            rows = self.toolbox.connection.execute(
                f"SELECT {_CASE_COLUMNS} FROM read_parquet(?) ORDER BY received_at, id",
                [str(path)],
            ).fetchall()
        return [_case_from_row(row) for row in rows]

    def events(self) -> list[Event]:
        rows = self.toolbox.connection.execute(
            """
            SELECT make, model, year, "group" AS group_name, event_type,
                   event_date, source_id
            FROM events
            ORDER BY event_date, source_id
            """
        ).fetchall()
        events: list[Event] = []
        for make, model, year, group_name, event_type, event_date, source_id in rows:
            kind = str(event_type)
            if kind not in ("recall", "investigation"):
                continue
            events.append(
                Event(
                    make=str(make),
                    model=str(model),
                    year=int(year),
                    group=str(group_name or ""),
                    event_type=cast("Any", kind),
                    event_date=_as_date(event_date),
                    source_id=str(source_id),
                )
            )
        return events

    def event_texts(self) -> tuple[dict[str, str], dict[str, str]]:
        """Return recall and investigation summaries keyed by id."""

        recalls = {
            str(row[0]): str(row[1] or "")
            for row in self.toolbox.connection.execute(
                "SELECT id, summary FROM recalls"
            ).fetchall()
        }
        investigations = {
            str(row[0]): str(row[1] or "")
            for row in self.toolbox.connection.execute(
                "SELECT id, summary FROM investigations"
            ).fetchall()
        }
        return recalls, investigations

    def close(self) -> None:
        self.toolbox.close()
        if self.temp_dir is not None:
            self.temp_dir.cleanup()


def _build_fixture_db(sql_path: Path, destination: Path) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    connection = duckdb.connect(str(destination))
    try:
        connection.execute(sql)
    finally:
        connection.close()


@contextmanager
def open_source(
    *,
    data_dir: str | Path | None = None,
    db_path: str | Path | None = None,
    fixture_sql: str | Path | None = None,
    rulebook_path: str | Path | None = None,
) -> Iterator[RunSource]:
    """Open exactly one source and clean up a temporary fixture database."""

    chosen = [item for item in (db_path, fixture_sql) if item is not None]
    if len(chosen) > 1:
        raise ValueError("pass either a fixture DB or fixture SQL, not both")
    temp: tempfile.TemporaryDirectory[str] | None = None
    source: RunSource | None = None
    try:
        if fixture_sql is not None:
            temp = tempfile.TemporaryDirectory(prefix="fqa-fixture-")
            db_file = Path(temp.name) / "fixture.duckdb"
            _build_fixture_db(Path(fixture_sql), db_file)
            toolbox = Toolbox.open(db_path=db_file, rulebook_path=rulebook_path)
            source = RunSource(toolbox=toolbox, db_path=db_file, temp_dir=temp)
        elif db_path is not None:
            toolbox = Toolbox.open(db_path=Path(db_path), rulebook_path=rulebook_path)
            source = RunSource(toolbox=toolbox, db_path=Path(db_path))
        else:
            directory = Path(data_dir or "data")
            toolbox = Toolbox.open(data_dir=directory, rulebook_path=rulebook_path)
            source = RunSource(toolbox=toolbox, data_dir=directory)
        yield source
    finally:
        if source is not None:
            source.close()
        elif temp is not None:
            temp.cleanup()
