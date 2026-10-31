"""Seeded sampling and export determinism."""

from __future__ import annotations

from pathlib import Path

import duckdb

from conftest import copy_groups
from field_quality_agents.data.build import _pick, _quotas, build_all


def _candidate_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        "CREATE TABLE candidates_all("
        "id VARCHAR, group_id VARCHAR, safety_relevant BOOLEAN, received_at DATE)"
    )
    rows = [
        (f"a{index:02d}", "a", index % 4 == 0, "2025-06-01")
        for index in range(20)
    ] + [
        (f"b{index:02d}", "b", index % 4 == 0, "2025-06-01")
        for index in range(20)
    ]
    con.executemany("INSERT INTO candidates_all VALUES (?, ?, ?, ?)", rows)


def test_quotas_respect_the_target_floor_and_caps() -> None:
    assert sum(_quotas({"a": 100, "b": 1, "c": 0}, 50, 10).values()) == 50
    assert _quotas({"a": 100, "b": 1}, 1000, 10) == {"a": 100, "b": 1}
    assert sum(_quotas({"a": 1, "b": 1, "c": 1}, 5, 10).values()) == 3
    assert _quotas({}, 10, 5) == {}


def test_pick_is_deterministic_for_the_same_seed() -> None:
    con = duckdb.connect()
    _candidate_table(con)
    quotas = {"a": 3, "b": 2}
    _pick(con, "candidates_all", quotas, "seed-1", "first")
    _pick(con, "candidates_all", quotas, "seed-1", "second")
    _pick(con, "candidates_all", quotas, "seed-2", "third")

    first = con.execute("SELECT id FROM first ORDER BY id").fetchall()
    second = con.execute("SELECT id FROM second ORDER BY id").fetchall()
    third = con.execute("SELECT id FROM third ORDER BY id").fetchall()
    assert first == second
    assert len(first) == 5
    assert first != third


def test_build_outputs_are_byte_identical_for_the_same_snapshot(
    tmp_path: Path, fixture_raw: Path
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    copy_groups(first)
    copy_groups(second)
    build_all(raw_dir=fixture_raw, out_dir=first)
    build_all(raw_dir=fixture_raw, out_dir=second)
    for name in (
        "kb_complaints.parquet",
        "replay_2025.parquet",
        "final_live.parquet",
        "events.parquet",
        "STATS.md",
    ):
        assert (first / name).read_bytes() == (second / name).read_bytes()
