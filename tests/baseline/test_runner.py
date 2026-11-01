"""End-to-end runner test on a tiny committed-shaped parquet fixture."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import duckdb

from field_quality_agents.baseline import load_cases, run_baseline

REPO_ROOT = Path(__file__).resolve().parents[2]
KEYWORDS = REPO_ROOT / "config" / "keywords.toml"

def _row(
    case_id: str,
    received: date,
    component: str,
    group: str,
    narrative: str,
    *,
    safety: bool = False,
) -> tuple[object, ...]:
    return (
        case_id,
        received,
        "HONDA",
        "ACCORD",
        2020,
        component,
        group,
        narrative,
        safety,
        42_000,
    )


def _write_parquet(path: Path, rows: list[tuple[object, ...]]) -> None:
    connection = duckdb.connect(":memory:")
    connection.execute("SET threads = 1")
    try:
        connection.execute(
            """
            CREATE TABLE cases (
                id VARCHAR, received_at DATE, make VARCHAR, model VARCHAR,
                year INTEGER, component VARCHAR, "group" VARCHAR,
                narrative VARCHAR, safety_relevant BOOLEAN, mileage INTEGER
            )
            """
        )
        connection.executemany(
            "INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        escaped = str(path).replace("'", "''")
        connection.execute(f"COPY cases TO '{escaped}' (FORMAT PARQUET)")
    finally:
        connection.close()


def _fixture_data(root: Path) -> Path:
    data = root / "data"
    data.mkdir(parents=True, exist_ok=True)

    training = [
        _row("K1", date(2021, 1, 1), "ELECTRICAL SYSTEM:WIRING", "power_and_wiring",
             "The wiring harness and battery cable corrode."),
        _row("K2", date(2021, 1, 2), "ELECTRICAL SYSTEM:12V/24V/48V BATTERY", "power_and_wiring",
             "The battery cable and wiring harness corrode."),
        _row("K3", date(2021, 1, 3), "EXTERIOR LIGHTING", "lighting",
             "The headlight bulb burns out at night."),
        _row("K4", date(2021, 1, 4), "EXTERIOR LIGHTING:BRAKE LIGHTS", "lighting",
             "The headlight and brake light bulb fail at night."),
    ]
    replay = [
        _row("C1", date(2025, 2, 3), "ELECTRICAL SYSTEM:WIRING", "power_and_wiring",
             "The wiring harness corroded near the battery cable."),
        _row("C2", date(2025, 2, 4), "EXTERIOR LIGHTING", "lighting",
             "The headlight bulb keeps failing at night.", safety=False),
        _row("C3", date(2025, 2, 5), "ELECTRICAL SYSTEM:WIRING", "power_and_wiring",
             "The wiring harness caught fire while driving.", safety=True),
    ]
    _write_parquet(data / "kb_complaints.parquet", training)
    _write_parquet(data / "replay_2025.parquet", replay)
    return data


def test_runner_writes_deterministic_results(tmp_path: Path) -> None:
    data = _fixture_data(tmp_path)
    output = tmp_path / "results"

    report = run_baseline(data_dir=data, out_dir=output, keywords_path=KEYWORDS)

    assert report.cases == 3
    assert report.priority == 1
    assert report.standard_test == 2
    assert report.no_trouble_found == 2

    for name in ("decisions.json", "metrics.json", "tfidf.json", "SUMMARY.md"):
        assert (output / name).is_file()

    first = {path.name: path.read_bytes() for path in output.iterdir() if path.is_file()}
    run_baseline(data_dir=data, out_dir=output, keywords_path=KEYWORDS)
    second = {path.name: path.read_bytes() for path in output.iterdir() if path.is_file()}
    assert first == second


def test_runner_outputs_are_stable_and_parse(tmp_path: Path) -> None:
    data = _fixture_data(tmp_path)
    output = tmp_path / "results"
    run_baseline(data_dir=data, out_dir=output, keywords_path=KEYWORDS)

    decisions = json.loads((output / "decisions.json").read_text())
    assert [decision["case_id"] for decision in decisions] == ["C1", "C2", "C3"]
    assert decisions[2]["route"] == "priority"
    assert decisions[2]["closed_no_trouble_found"] is False

    metrics = json.loads((output / "metrics.json").read_text())
    assert metrics["cases"] == 3
    assert 0.0 <= metrics["group_macro_f1"]["value"] <= 1.0

    tfidf = json.loads((output / "tfidf.json").read_text())
    assert tfidf["train_size"] == 4
    assert tfidf["test_size"] == 3
    assert len(tfidf["predictions"]) == 3

    summary = (output / "SUMMARY.md").read_text()
    assert "Linear baseline" in summary
    assert "closed no trouble found | 2" in summary


def test_loader_preserves_the_contract_fields(tmp_path: Path) -> None:
    data = _fixture_data(tmp_path)
    cases = load_cases(data / "replay_2025.parquet")
    assert [case.id for case in cases] == ["C1", "C2", "C3"]
    assert cases[0].group == "power_and_wiring"
    assert cases[0].mileage == 42_000
    assert isinstance(cases[0].received_at, date)
