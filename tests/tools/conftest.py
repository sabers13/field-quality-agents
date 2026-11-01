"""Fixture DuckDB and the process-wide toolbox for tool tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest

from field_quality_agents.tools import Toolbox, configure, reset_default

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
REPO_ROOT = Path(__file__).resolve().parents[2]
RULEBOOK = REPO_ROOT / "config" / "rulebook.toml"


@pytest.fixture(scope="session")
def fixture_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("tools") / "tools.duckdb"
    sql = (FIXTURES / "tools_fixture.sql").read_text(encoding="utf-8")
    connection = duckdb.connect(str(path))
    try:
        connection.execute(sql)
    finally:
        connection.close()
    return path


@pytest.fixture(autouse=True)
def toolbox(fixture_db: Path) -> Iterator[Toolbox]:
    configured = configure(db_path=fixture_db, rulebook_path=RULEBOOK)
    yield configured
    reset_default()
