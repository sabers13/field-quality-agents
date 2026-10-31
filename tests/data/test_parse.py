"""Parsing the headerless, tab-delimited NHTSA files."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from conftest import complaint_rows
from field_quality_agents.data.schema import COMPLAINT_COLUMNS, read_complaints


def _write(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write("\t".join(row) + "\n")


def test_read_complaints_keeps_quotes_and_all_columns(tmp_path: Path) -> None:
    narrative = (
        'He said "the harness" was loose and then the dash went dark. '
        "The dealer could not reproduce the fault after two visits."
    )
    rows = [
        *complaint_rows("9001", "20210101", narrative=narrative),
        *complaint_rows("9002", "20220202", components=["AIR BAGS"], crash="Y"),
    ]
    path = tmp_path / "CMPL.txt"
    _write(path, rows)

    con = duckdb.connect()
    read_complaints(con, [path])
    assert len(con.execute("DESCRIBE complaints_raw").fetchall()) == len(
        COMPLAINT_COLUMNS
    )
    result = con.execute(
        "SELECT CMPLID, CDESCR, COMPDESC, CRASH FROM complaints_raw ORDER BY CMPLID"
    ).fetchall()
    assert result[0][0] == "9001"
    assert result[0][1] == narrative
    assert result[0][2] == "ELECTRICAL SYSTEM:WIRING"
    assert result[0][3] == "N"
    assert result[1][3] == "Y"


def test_read_complaints_rejects_a_short_row(tmp_path: Path) -> None:
    path = tmp_path / "bad.txt"
    path.write_text("1\t2\t3\n", encoding="utf-8")
    con = duckdb.connect()
    with pytest.raises(duckdb.Error):
        read_complaints(con, [path])
