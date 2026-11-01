"""Q8 end-to-end: replay the fixture recordings and check the run artifacts."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pytest

from field_quality_agents.agents.report import week_bounds
from field_quality_agents.contracts import CaseStatus, DecisionActor, RunMode
from field_quality_agents.llm.errors import ReplayMissError
from field_quality_agents.metrics.evidence import SourceIndex, citation_validity
from field_quality_agents.run.data import open_source
from field_quality_agents.run.pipeline import execute_run
from field_quality_agents.run.writer import read_json

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_SQL = ROOT / "tests" / "fixtures" / "e2e" / "replay_2025.sql"
RECORDINGS = ROOT / "tests" / "fixtures" / "recordings"


def _run(tmp_path: Path, run_id: str = "test-run"):
    with open_source(fixture_sql=FIXTURE_SQL) as source:
        cases = source.cases()
        summary = execute_run(
            source=source,
            recordings_dir=RECORDINGS,
            results_dir=tmp_path / "runs",
            run_id=run_id,
            set_name="replay_2025",
            mode=RunMode.REPLAY,
        )
    return cases, summary


def _digest(directory: Path) -> dict[str, str]:
    return {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def test_two_replays_are_byte_identical(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _run(first)
    _run(second)

    assert _digest(first / "runs" / "test-run") == _digest(second / "runs" / "test-run")


def test_run_writes_every_documented_artifact(tmp_path: Path) -> None:
    cases, summary = _run(tmp_path)
    directory = summary.directory

    assert summary.cases == len(cases) == 16
    assert summary.issues == 1
    assert summary.reports == 3
    manifest = read_json(directory / "manifest.json")
    assert manifest["status"] == "complete"
    assert manifest["case_count"] == 16
    assert manifest["record_digest"]
    for name in (
        "cases.json",
        "traces.json",
        "proposals.json",
        "decisions.json",
        "issues.json",
        "eight_d.json",
        "memos.json",
        "report.json",
        "reports.json",
        "metrics.json",
        "manifest.json",
        "events.json",
        "evidence.json",
        "tool_outputs.json",
    ):
        assert (directory / name).is_file(), name

    decisions = read_json(directory / "decisions.json")
    assert decisions
    assert {decision["actor"] for decision in decisions} == {
        DecisionActor.SIMULATED_ENGINEER.value
    }
    cases_payload = read_json(directory / "cases.json")
    decided = [
        item["id"] for item in cases_payload if item["status"] == CaseStatus.DECIDED.value
    ]
    assert decided
    decisions_by_case = {item["case_id"] for item in decisions}
    assert set(decided) <= decisions_by_case

    events = read_json(directory / "events.json")
    assert [event["seq"] for event in events] == list(range(1, len(events) + 1))
    assert {event["kind"] for event in events} >= {
        "case",
        "trace",
        "decision",
        "issue",
        "report",
    }


def test_issue_and_report_numbers_come_from_the_run_tables(tmp_path: Path) -> None:
    cases, summary = _run(tmp_path)
    directory = summary.directory
    issues = read_json(directory / "issues.json")
    assert len(issues) == 1
    issue = issues[0]
    assert issue["opened_at"] == "2025-06-09"
    assert issue["observed"] >= issue["threshold"]
    assert issue["linked_case_ids"]
    assert issue["linked_recall_ids"]
    assert issue["linked_investigation_ids"]
    case_ids = {case.id for case in cases}
    assert set(issue["linked_case_ids"]) <= case_ids

    reports = [
        *read_json(directory / "reports.json"),
        read_json(directory / "report.json"),
    ]
    reports.sort(key=lambda report: report["week_start"])
    assert len(reports) == 3
    for report in reports:
        start = date.fromisoformat(report["week_start"])
        end = date.fromisoformat(report["week_end"])
        assert week_bounds(start) == (start, end)
        received = [case for case in cases if start <= case.received_at <= end]
        assert report["cases_received"] == len(received)
        assert report["open_issues"] >= 0
        assert "Every figure is counted" in report["narrative"]


def test_drafts_cite_real_ids_and_pass_citation_validity(tmp_path: Path) -> None:
    cases, summary = _run(tmp_path)
    directory = summary.directory
    with open_source(fixture_sql=FIXTURE_SQL) as source:
        recalls, investigations = source.event_texts()
    sources = SourceIndex(
        cases={case.id: case.narrative for case in cases},
        recalls=recalls,
        investigations=investigations,
    )
    drafts = read_json(directory / "eight_d.json")
    memos = read_json(directory / "memos.json")
    assert drafts and memos
    from field_quality_agents.contracts import Citation

    for document in [*drafts, *memos]:
        citations = tuple(Citation.model_validate(item) for item in document["citations"])
        assert citation_validity(citations, sources).value == 1.0
        ids = [citation.source_id for citation in citations]
        statements = [
            document.get("d2_problem", ""),
            document.get("d3_containment", ""),
            *document.get("d4_root_cause_hypotheses", []),
            document.get("body", ""),
        ]
        for statement in statements:
            if not statement:
                continue
            if document.get("body"):
                for paragraph in statement.split("\n\n"):
                    assert any(identifier in paragraph for identifier in ids)
            else:
                assert any(identifier in statement for identifier in ids)


def test_a_replay_miss_is_an_error(tmp_path: Path) -> None:
    empty = tmp_path / "empty-recordings"
    empty.mkdir()
    with open_source(fixture_sql=FIXTURE_SQL) as source, pytest.raises(ReplayMissError):
        execute_run(
            source=source,
            recordings_dir=empty,
            results_dir=tmp_path / "runs",
            run_id="miss",
            set_name="replay_2025",
            mode=RunMode.REPLAY,
        )
