"""Export one recorded run as the dashboard's bundled JSON data.

Q10 owns the final offline portfolio export. Q8 writes the data half of it in
the shapes frozen in ``docs/INTERFACES.md`` so ``make all`` has an export step
and the dashboard can be built against a real recorded run.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, time
from pathlib import Path

from field_quality_agents.api.events import feed_from_store
from field_quality_agents.api.kpis import build_command_centre, build_comparison, build_summary
from field_quality_agents.api.models import (
    CaseDetail,
    CaseListItem,
    ComparisonExample,
    IssueDetail,
    IssueSummary,
    ReplayEvent,
    ReplayRun,
)
from field_quality_agents.api.store import CaseRecord, FileResultStore, IssueRecord
from field_quality_agents.run.writer import write_json

__all__ = ["export_dashboard"]


def _item(record: CaseRecord) -> CaseListItem:
    case = record.case
    evidence = 0
    if record.proposal is not None:
        evidence = sum(1 for citation in record.proposal.evidence if citation.verified)
    touches = sum(
        1 for step in record.trace if step.agent in ("human", "live_engineer")
    )
    return CaseListItem(
        id=case.id,
        received_at=case.received_at,
        make=case.make,
        model=case.model,
        year=case.year,
        component=case.component,
        group=case.group,
        status=case.status,
        safety_relevant=case.safety_relevant,
        evidence_count=evidence,
        human_touches=max(touches, 1 if record.decision is not None else 0),
    )


def _detail(store: FileResultStore, record: CaseRecord) -> CaseDetail:
    evidence = store.evidence(record.case.id)
    return CaseDetail(
        case=record.case,
        extraction=record.extraction,
        proposal=record.proposal,
        trace=list(record.trace),
        decision=record.decision,
        similar_cases=list(evidence.similar_cases),
        recalls=list(evidence.recalls),
        investigations=list(evidence.investigations),
    )


def _issue_summary(record: IssueRecord) -> IssueSummary:
    issue = record.issue
    return IssueSummary(
        id=issue.id,
        title=issue.title,
        status=issue.status,
        opened_at=issue.opened_at,
        make=issue.make,
        model=issue.model,
        year=issue.year,
        group=issue.group,
        observed=issue.observed,
        threshold=issue.threshold,
        spike_ratio=issue.spike_ratio,
        linked_case_count=len(issue.linked_case_ids),
    )


def _issue_detail(record: IssueRecord) -> IssueDetail:
    issue = record.issue
    summary = _issue_summary(record)
    return IssueDetail(
        **summary.model_dump(),
        weekly_counts=list(issue.weekly_counts),
        linked_case_ids=list(issue.linked_case_ids),
        linked_recall_ids=list(issue.linked_recall_ids),
        linked_investigation_ids=list(issue.linked_investigation_ids),
        eight_d=record.eight_d,
        memo=record.memo,
    )


def export_dashboard(
    *,
    results_dir: str | Path = "results/runs",
    run_id: str | None = None,
    out_dir: str | Path = "dist/field-quality-agents",
    examples: Sequence[ComparisonExample] | None = None,
) -> Path:
    """Write ``data/`` for the dashboard and return the export root.

    ``examples`` overrides the run's stored showcase examples; Q10 passes the
    fixed-rule selection from ``export/showcase.py`` so the export and the
    committed run records stay independent.
    """

    store = FileResultStore(results_dir, run_id=run_id)
    active = store.active_run_id()
    if active is None:
        raise ValueError(f"no recorded run under {results_dir}")
    root = Path(out_dir)
    data = root / "data"
    records = list(store.cases())
    issues = list(store.issues())
    # An explicit run id exports that run only. This keeps `make all`
    # byte-identical no matter which record-mode runs sit beside it.
    selected = [
        run for run in store.runs() if run_id is None or run.run_id == active
    ]
    runs = [
        ReplayRun(
            run_id=run.run_id,
            set_name=run.set_name,
            started_at=run.started_at,
            status=run.status,
            case_count=run.case_count,
        )
        for run in selected
    ]
    events = {
        run.run_id: [
            ReplayEvent(
                seq=event.seq,
                at=event.at,
                kind=event.kind,
                case_id=event.case_id,
                issue_id=event.issue_id,
                payload=dict(event.payload),
            )
            for event in store.replay_events(run.run_id)
        ]
        for run in selected
    }
    command = build_command_centre(
        store=store,
        window="365d",
        feed=feed_from_store(store),
    )
    if examples is not None:
        command = command.model_copy(
            update={"comparison": build_summary(store.metrics(), examples)}
        )
    comparison = build_comparison(
        store.metrics(),
        store.comparison_examples() if examples is None else examples,
    )
    reports = sorted(
        store.weekly_reports(),
        key=lambda report: (report.week_start, report.week_end),
    )
    latest_report = reports[-1] if reports else None
    latest_case = max(
        (record.case.received_at for record in records),
        default=None,
    )
    generated_at = (
        datetime.combine(latest_case, time(23, 59), tzinfo=UTC)
        if latest_case is not None
        else datetime(1970, 1, 1, tzinfo=UTC)
    )

    files: list[str] = []
    write_json(data / "command_centre.json", command.model_dump(mode="json"))
    files.append("command_centre.json")

    write_json(
        data / "cases.json",
        [_item(record).model_dump(mode="json") for record in records],
    )
    files.append("cases.json")
    for record in records:
        name = f"cases/{record.case.id}.json"
        write_json(
            data / name,
            _detail(store, record).model_dump(mode="json"),
        )
        files.append(name)

    write_json(
        data / "issues.json",
        [_issue_detail(record).model_dump(mode="json") for record in issues],
    )
    files.append("issues.json")
    write_json(
        data / "comparison.json",
        comparison.model_dump(mode="json") if comparison is not None else None,
    )
    files.append("comparison.json")
    write_json(
        data / "weekly_report.json",
        latest_report.model_dump(mode="json") if latest_report is not None else None,
    )
    files.append("weekly_report.json")
    write_json(
        data / "replay.json",
        {
            "runs": [run.model_dump(mode="json") for run in runs],
            "events": {
                run_id_key: [event.model_dump(mode="json") for event in items]
                for run_id_key, items in sorted(events.items())
            },
        },
    )
    files.append("replay.json")

    manifest = {
        "run_id": active,
        "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
        "files": sorted([*files, "manifest.json"]),
        "counts": {
            "cases": len(records),
            "issues": len(issues),
            "weeks": len(reports),
            "events": sum(len(items) for items in events.values()),
        },
    }
    write_json(data / "manifest.json", manifest)
    return root
