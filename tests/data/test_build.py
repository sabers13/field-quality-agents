"""End-to-end build over a tiny synthetic snapshot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pytest

from conftest import copy_groups
from field_quality_agents.data.build import build_all

COMPLAINT_COLUMNS = [
    "id",
    "received_at",
    "make",
    "model",
    "year",
    "component",
    "group",
    "narrative",
    "safety_relevant",
    "mileage",
]


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory, fixture_raw: Path) -> tuple[Any, Path]:
    out = tmp_path_factory.mktemp("derived")
    copy_groups(out)
    result = build_all(raw_dir=fixture_raw, out_dir=out)
    return result, out


def _read(out: Path, name: str, query: str) -> list[tuple[Any, ...]]:
    con = duckdb.connect()
    return con.execute(
        f"SELECT {query} FROM read_parquet(?)", [str(out / f"{name}.parquet")]
    ).fetchall()


def test_outputs_and_schemas(built: tuple[Any, Path]) -> None:
    result, out = built
    expected = {
        "kb_complaints.parquet",
        "recalls.parquet",
        "investigations.parquet",
        "replay_2025.parquet",
        "final_live.parquet",
        "fleet_weekly.parquet",
        "events.parquet",
        "STATS.md",
    }
    assert {path.name for path in result.outputs} == expected
    assert all(path.is_file() for path in result.outputs)

    con = duckdb.connect()
    columns = [
        row[0]
        for row in con.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [str(out / "kb_complaints.parquet")],
        ).fetchall()
    ]
    assert columns == COMPLAINT_COLUMNS
    for dropped in (
        "city",
        "state",
        "vin",
        "dealer_name",
        "dealer_tel",
        "dealer_city",
        "dealer_zip",
        "vehicle_operator",
        "mfr_name",
    ):
        assert dropped not in columns


def test_single_group_rule_and_filters(built: tuple[Any, Path]) -> None:
    result, out = built
    ids = {row[0] for row in _read(out, "kb_complaints", "id")}
    assert ids == {"C1", "C2"}
    stats = result.stats["complaints"]
    assert stats["single_group_complaints"] == 9
    assert stats["narrative_under_80_dropped"] == 1
    assert stats["pii_dropped"] == 1
    assert stats["missing_product_key_dropped"] == 1
    assert stats["eligible_complaints"] == 6


def test_replay_selection_is_2025_and_safety_aware(built: tuple[Any, Path]) -> None:
    result, out = built
    rows = _read(out, "replay_2025", "id, year, safety_relevant, received_at")
    assert {row[0] for row in rows} == {"C7", "C8"}
    assert sum(1 for row in rows if row[2]) == 1
    assert [row[3].year for row in rows] == [2025, 2025]
    assert result.stats["sets"]["replay"]["safety_relevant"] == 1


def test_final_live_uses_the_last_complete_weeks(built: tuple[Any, Path]) -> None:
    result, out = built
    rows = _read(out, "final_live", "id, received_at")
    assert {row[0] for row in rows} == {"C9"}
    assert result.stats["final_window"]["sealed"] is True
    assert result.stats["final_window"]["start"] == "2026-09-28"
    assert result.stats["final_window"]["end"] == "2026-10-25"


def test_recalls_and_investigations_keep_unmapped_rows(built: tuple[Any, Path]) -> None:
    _, out = built
    recalls = _read(out, "recalls", 'id, "group", open_date')
    by_id = {row[0]: row for row in recalls}
    assert by_id["R1"][1] == "power_and_wiring"
    assert by_id["R2"][1] is None
    assert by_id["R1"][2].isoformat() == "2021-03-01"

    investigations = _read(out, "investigations", 'id, "group", open_date')
    assert investigations[0][0] == "I1"
    assert investigations[0][1] == "adas"
    assert investigations[0][2].isoformat() == "2022-03-01"


def test_event_ground_truth_joins_fleet_keys(built: tuple[Any, Path]) -> None:
    result, out = built
    events = _read(
        out, "events", 'make, model, year, "group", event_type, event_date, source_id'
    )
    assert {row[6] for row in events} == {"R1", "I1"}
    assert {row[4] for row in events} == {"recall", "investigation"}
    assert result.stats["events"]["rows"] == 2
    assert result.stats["events"]["joined_to_fleet"] == 2


def test_fleet_weekly_counts_all_mapped_cases(built: tuple[Any, Path]) -> None:
    _, out = built
    rows = _read(out, "fleet_weekly", 'week_start, make, model, year, "group", count')
    assert rows
    assert all(row[0].weekday() == 0 for row in rows)
    total = sum(row[5] for row in rows)
    assert total == 8
    assert any(row[1] == "HONDA" and row[2] == "ACCORD" and row[3] == 2021 for row in rows)


def test_stats_file_reports_pii_and_mapping_rates(built: tuple[Any, Path]) -> None:
    _, out = built
    text = (out / "STATS.md").read_text(encoding="utf-8")
    assert "PII screen" in text
    assert "email" in text
    assert "power_and_wiring" in text
    assert "sealed" in text
    assert "recalls" in text
    assert "investigations" in text
