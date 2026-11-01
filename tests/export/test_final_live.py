"""Q14's final live panel reads only committed run files."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from field_quality_agents.contracts import (
    MetricEstimate,
    Metrics,
    RunManifest,
    RunMode,
    RunStatus,
)
from field_quality_agents.export.final_live import load_final_live


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _pair(cases: int, precision: float) -> dict[str, object]:
    metrics = Metrics(
        cases=cases,
        safety_precision=MetricEstimate(value=precision, ci_low=None, ci_high=None, n=cases),
    )
    return {"before": metrics.model_dump(mode="json"), "after": metrics.model_dump(mode="json")}


def _manifest(run_id: str, set_name: str, cases: int) -> RunManifest:
    return RunManifest(
        run_id=run_id,
        mode=RunMode.RECORD,
        set_name=set_name,
        started_at=datetime(2026, 9, 28, 6, 0, tzinfo=UTC),
        completed_at=datetime(2026, 10, 25, 23, 59, tzinfo=UTC),
        status=RunStatus.COMPLETE,
        case_count=cases,
        spend_usd=0.25,
        steps=600,
    )


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    final = tmp_path / "final-live"
    manifest = _manifest("final-live", "final_live", 150)
    _write(final / "manifest.json", manifest.model_dump(mode="json"))
    _write(final / "metrics.json", _pair(150, 0.5))
    q9 = tmp_path / "runs" / "replay" / "metrics.json"
    _write(q9, _pair(600, 0.4482))
    return final, q9


def test_panel_compares_the_two_runs(tmp_path: Path) -> None:
    final, q9 = _fixture(tmp_path)

    data = load_final_live(final_dir=final, q9_metrics=q9)

    assert data is not None
    assert data.run_id == "final-live"
    assert data.set_name == "final_live"
    assert data.window_start.isoformat() == "2026-09-28"
    assert data.window_end.isoformat() == "2026-10-25"
    assert data.final.cases == 150
    assert data.q9.cases == 600
    assert data.q9_run_id == "replay"
    assert data.final.after.safety_precision is not None
    assert data.final.after.safety_precision.value == 0.5


def test_panel_is_absent_without_the_run(tmp_path: Path) -> None:
    assert (
        load_final_live(
            final_dir=tmp_path / "missing",
            q9_metrics=tmp_path / "none.json",
        )
        is None
    )
