"""One DuckDB connection and the derived tables the tools read.

The committed parquet files are the source of truth. A :class:`Toolbox`
creates an in-memory DuckDB connection and exposes views with stable names
(``complaints``, ``cases``, ``recalls``, ``investigations``, ``events``,
``fleet_weekly``) over those files. Tests can point it at a small fixture
DuckDB file instead; the tools never rebuild the data and never read the
sealed ``final_live`` set.

The default toolbox is process-wide. ``configure`` replaces it, which is how
the MCP server and tests select a database. The public module functions in
:mod:`field_quality_agents.tools` delegate to it, so callers see the frozen
signatures from ``docs/INTERFACES.md``.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb

__all__ = ["Toolbox", "configure", "get_toolbox", "reset_default"]

_DEFAULT_DATA_DIR = Path("data")
_DEFAULT_RULEBOOK = Path("config/rulebook.toml")


def _quote_sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _default_rulebook_path() -> Path:
    explicit = os.environ.get("FQA_RULEBOOK")
    if explicit:
        return Path(explicit)
    candidates = (
        Path.cwd() / _DEFAULT_RULEBOOK,
        Path(__file__).resolve().parents[3] / _DEFAULT_RULEBOOK,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def _resolve_rulebook(path: str | Path | None) -> Path:
    if path is not None:
        return Path(path)
    return _default_rulebook_path()


class Toolbox:
    """A configured DuckDB connection plus the rulebook location."""

    def __init__(self, connection: duckdb.DuckDBPyConnection, rulebook_path: Path) -> None:
        self.connection = connection
        self.rulebook_path = rulebook_path
        self._search_ready = False
        self._closed = False

    @classmethod
    def open(
        cls,
        *,
        data_dir: str | Path | None = None,
        db_path: str | Path | None = None,
        rulebook_path: str | Path | None = None,
    ) -> Toolbox:
        """Open the committed parquet files or a fixture DuckDB file.

        ``db_path`` wins when both are given. A data directory must contain
        the committed parquet files written by Q1.
        """

        connection = duckdb.connect(":memory:")
        connection.execute("SET threads = 1")
        connection.execute("SET preserve_insertion_order = true")
        try:
            if db_path is not None:
                _attach_fixture(connection, Path(db_path))
            else:
                _attach_data_dir(connection, Path(data_dir or _DEFAULT_DATA_DIR))
        except Exception:
            connection.close()
            raise
        return cls(connection, _resolve_rulebook(rulebook_path))

    def ensure_search_index(self) -> None:
        """Materialise the token table used by BM25, once per connection."""

        if self._search_ready:
            return
        self.connection.execute(
            """
            CREATE OR REPLACE TEMP TABLE fqa_docs AS
            SELECT id,
                   make,
                   model,
                   year,
                   "group",
                   safety_relevant,
                   narrative,
                   len(regexp_extract_all(lower(coalesce(narrative, '')), '[a-z0-9]+')) AS dl
            FROM complaints
            """
        )
        self.connection.execute(
            """
            CREATE OR REPLACE TEMP TABLE fqa_tokens AS
            SELECT id,
                   unnest(regexp_extract_all(lower(coalesce(narrative, '')), '[a-z0-9]+')) AS token
            FROM complaints
            """
        )
        self._search_ready = True

    def close(self) -> None:
        if not self._closed:
            self.connection.close()
            self._closed = True

    def __enter__(self) -> Toolbox:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _attach_parquet(connection: duckdb.DuckDBPyConnection, name: str, path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"missing committed data file: {path}")
    connection.execute(
        f"CREATE VIEW {name} AS SELECT * FROM read_parquet({_quote_sql_string(str(path))})"
    )


def _attach_data_dir(connection: duckdb.DuckDBPyConnection, data_dir: Path) -> None:
    data_dir = data_dir.resolve()
    complaints = data_dir / "kb_complaints.parquet"
    replay = data_dir / "replay_2025.parquet"
    _attach_parquet(connection, "complaints", complaints)
    _attach_parquet(connection, "recalls", data_dir / "recalls.parquet")
    _attach_parquet(connection, "investigations", data_dir / "investigations.parquet")
    _attach_parquet(connection, "events", data_dir / "events.parquet")
    _attach_parquet(connection, "fleet_weekly", data_dir / "fleet_weekly.parquet")
    if replay.is_file():
        connection.execute(
            "CREATE VIEW cases AS "
            f"SELECT * FROM read_parquet({_quote_sql_string(str(complaints))}) "
            "UNION ALL "
            f"SELECT * FROM read_parquet({_quote_sql_string(str(replay))})"
        )
    else:
        connection.execute("CREATE VIEW cases AS SELECT * FROM complaints")


def _attach_fixture(connection: duckdb.DuckDBPyConnection, path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"missing fixture DuckDB: {path}")
    connection.execute(f"ATTACH {_quote_sql_string(str(path))} AS source (READ_ONLY)")
    names = {
        str(row[0])
        for row in connection.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_catalog = 'source'"
        ).fetchall()
    }
    required = {"recalls", "investigations", "fleet_weekly"}
    missing = sorted(required - names)
    if missing:
        raise ValueError(f"fixture DuckDB is missing table(s): {', '.join(missing)}")
    has_complaints = "complaints" in names
    has_cases = "cases" in names
    if not has_complaints and not has_cases:
        raise ValueError("fixture DuckDB must define complaints or cases")
    complaints_source = "complaints" if has_complaints else "cases"
    connection.execute(
        f"CREATE VIEW complaints AS SELECT * FROM source.{complaints_source}"
    )
    if has_cases:
        connection.execute("CREATE VIEW cases AS SELECT * FROM source.cases")
    else:
        connection.execute("CREATE VIEW cases AS SELECT * FROM complaints")
    for table in ("recalls", "investigations", "fleet_weekly"):
        connection.execute(f"CREATE VIEW {table} AS SELECT * FROM source.{table}")
    if "events" in names:
        connection.execute("CREATE VIEW events AS SELECT * FROM source.events")


_default: Toolbox | None = None


def configure(
    *,
    data_dir: str | Path | None = None,
    db_path: str | Path | None = None,
    rulebook_path: str | Path | None = None,
) -> Toolbox:
    """Replace the process-wide toolbox and return it.

    With neither ``data_dir`` nor ``db_path``, the environment is used:
    ``FQA_DB`` first, then ``FQA_DATA_DIR`` (default ``data``). That is how
    ``fqa mcp`` follows the same settings as the rest of the project.
    """

    global _default
    if _default is not None:
        _default.close()
    if data_dir is None and db_path is None:
        _default = _open_from_environment(rulebook_path)
    else:
        _default = Toolbox.open(
            data_dir=data_dir,
            db_path=db_path,
            rulebook_path=rulebook_path,
        )
    return _default


def _open_from_environment(rulebook_path: str | Path | None = None) -> Toolbox:
    db_path = os.environ.get("FQA_DB")
    if db_path:
        return Toolbox.open(db_path=Path(db_path), rulebook_path=rulebook_path)
    data_dir = Path(os.environ.get("FQA_DATA_DIR", str(_DEFAULT_DATA_DIR)))
    return Toolbox.open(data_dir=data_dir, rulebook_path=rulebook_path)


def get_toolbox() -> Toolbox:
    global _default
    if _default is None:
        _default = _open_from_environment()
    return _default


def reset_default() -> None:
    """Close and forget the default toolbox (used by tests)."""

    global _default
    if _default is not None:
        _default.close()
        _default = None
