"""FileResultStore: the documented on-disk layout for Q8's runs."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest
from api_fixtures import (
    CASE_ID,
    DECIDED_ID,
    ISSUE_ID,
    NOW,
    RUN_ID,
    make_case,
    make_decision,
    make_eight_d,
    make_evidence,
    make_extraction,
    make_issue,
    make_manifest,
    make_memo,
    make_metrics,
    make_proposal,
    make_reports,
    make_trace,
)
from fastapi.testclient import TestClient

from field_quality_agents.api import FileResultStore, create_app
from field_quality_agents.api.store import ResultStoreError

OLD_RUN = "run-2025-02"


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _dump(model: object) -> object:
    return model.model_dump(mode="json")  # type: ignore[attr-defined]


def build_run(root: Path, run_id: str = RUN_ID, *, started_note: str = "new") -> Path:
    directory = root / run_id
    directory.mkdir(parents=True)
    manifest = make_manifest(run_id)
    _write(directory / "manifest.json", _dump(manifest))

    analysis = make_case()
    decided = make_case(
        DECIDED_ID,
        received_at=analysis.received_at,
        status=analysis.status,
        narrative="A second report.",
    )
    _write(directory / "cases.json", [_dump(analysis), _dump(decided)])
    _write(
        directory / "traces.json",
        {CASE_ID: [_dump(step) for step in make_trace(1, 3)], DECIDED_ID: []},
    )
    _write(directory / "extractions.json", {CASE_ID: _dump(make_extraction())})
    _write(
        directory / "proposals.json",
        {CASE_ID: _dump(make_proposal()), DECIDED_ID: _dump(make_proposal(DECIDED_ID))},
    )
    _write(
        directory / "decisions.json",
        [_dump(make_decision())],
    )
    evidence = make_evidence()
    recalls = [
        {
            "id": recall.id,
            "summary": recall.summary,
            "open_date": recall.open_date.isoformat(),
            "make": "Make A",
            "model": "Model B",
        }
        for recall in evidence.recalls
    ]
    investigations = [
        {
            "id": item.id,
            "summary": item.summary,
            "open_date": item.open_date.isoformat(),
        }
        for item in evidence.investigations
    ]
    _write(
        directory / "evidence.json",
        {
            CASE_ID: {
                "similar_cases": [_dump(item) for item in evidence.similar_cases],
                "recalls": recalls,
                "investigations": investigations,
            }
        },
    )
    _write(
        directory / "issues.json",
        [_dump(make_issue())],
    )
    _write(directory / "eight_d.json", [_dump(make_eight_d())])
    _write(directory / "memos.json", [_dump(make_memo())])
    earlier, latest = make_reports()
    _write(directory / "report.json", _dump(latest))
    _write(directory / "reports.json", [_dump(earlier)])
    before = make_metrics(touches=4.0, cost=30.0, targeted=0.0)
    after = make_metrics(touches=2.0, cost=12.0, targeted=0.4)
    _write(directory / "metrics.json", {"before": _dump(before), "after": _dump(after)})
    _write(
        directory / "events.json",
        [
            {
                "seq": 1,
                "at": "2025-03-11T09:00:00Z",
                "kind": "case",
                "case_id": CASE_ID,
                "payload": {"status": "intake"},
            },
            {
                "seq": 2,
                "at": "2025-03-11T09:05:00Z",
                "kind": "issue",
                "issue_id": ISSUE_ID,
                "payload": {"status": "open"},
            },
        ],
    )
    _write(
        directory / "comparison_examples.json",
        [
            {
                "case_id": CASE_ID,
                "before": "standard test",
                "after": "targeted test",
                "note": started_note,
            }
        ],
    )
    return directory


def test_file_store_reads_every_documented_file(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    build_run(root)

    store = FileResultStore(root)

    assert store.active_run_id() == RUN_ID
    assert [run.run_id for run in store.runs()] == [RUN_ID]
    records = {record.case.id: record for record in store.cases()}
    assert records[CASE_ID].proposal is not None
    assert records[CASE_ID].proposal.kind.value == "targeted_load_test"
    assert len(records[CASE_ID].trace) == 3
    assert records[DECIDED_ID].decision is not None
    assert records[DECIDED_ID].decision.action.value == "approve"

    evidence = store.evidence(CASE_ID)
    assert evidence.similar_cases[0].score == 0.8123
    assert evidence.recalls[0].id == "R-2024-01"
    assert evidence.investigations[0].id == "I-2024-02"

    issues = store.issues()
    assert len(issues) == 1
    assert issues[0].eight_d is not None
    assert issues[0].eight_d.d2_problem.startswith("Seven display")
    assert issues[0].memo is not None

    assert len(store.weekly_reports()) == 2
    assert store.metrics() is not None
    assert store.metrics().after.cases == 10
    assert store.comparison_examples()[0].note == "new"

    events = store.replay_events(RUN_ID)
    assert [event.seq for event in events] == [1, 2]
    assert store.replay_events("missing") == ()


def test_file_store_picks_the_newest_or_a_named_run(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    oldest = build_run(root, OLD_RUN, started_note="old")
    old_manifest = make_manifest(OLD_RUN).model_copy(
        update={"started_at": NOW - timedelta(days=1)}
    )
    _write(oldest / "manifest.json", _dump(old_manifest))

    newer_dir = root / RUN_ID
    newer_dir.mkdir()
    _write(newer_dir / "manifest.json", _dump(make_manifest(RUN_ID)))
    _write(newer_dir / "cases.json", [_dump(make_case("C-2025-0099"))])

    store = FileResultStore(root)
    assert [run.run_id for run in store.runs()] == [RUN_ID, OLD_RUN]
    assert store.active_run_id() == RUN_ID

    named = FileResultStore(root, run_id=OLD_RUN)
    assert named.active_run_id() == OLD_RUN
    assert named.cases()[0].case.id == CASE_ID


def test_file_store_tolerates_a_missing_root(tmp_path: Path) -> None:
    store = FileResultStore(tmp_path / "absent")

    assert store.runs() == ()
    assert store.cases() == ()
    assert store.metrics() is None
    assert store.weekly_reports() == ()


def test_file_store_reports_malformed_json(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    directory = build_run(root)
    (directory / "cases.json").write_text("{ not json", encoding="utf-8")

    store = FileResultStore(root)
    with pytest.raises(ResultStoreError, match=r"cases\.json"):
        store.cases()


def test_app_serves_a_file_backed_run(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    build_run(root)
    app = create_app(store=FileResultStore(root), mode="replay", static_dir=tmp_path / "dist")

    with TestClient(app) as client:
        detail = client.get(f"/api/cases/{CASE_ID}")
        assert detail.status_code == 200
        assert detail.json()["proposal"]["kind"] == "targeted_load_test"

        issue = client.get(f"/api/issues/{ISSUE_ID}")
        assert issue.status_code == 200
        assert issue.json()["memo"]["id"] == "M-1"

        events = client.get(f"/api/replay/runs/{RUN_ID}/events")
        assert [item["seq"] for item in events.json()["items"]] == [1, 2]

        report = client.get("/api/reports/weekly")
        assert report.status_code == 200
        assert report.json()["week_start"] == "2025-03-10"
