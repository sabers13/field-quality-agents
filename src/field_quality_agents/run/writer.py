"""Write one run directory in the layout the API store reads.

Every JSON file is sorted and newline-terminated so two runs over the same
recordings produce byte-identical files. The layout is documented in
``api/store.py``; this module is the writer side of that contract.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from field_quality_agents.api.models import ComparisonExample, ReplayEvent
from field_quality_agents.contracts import (
    Case,
    DecisionMemo,
    EightD,
    Extraction,
    HumanDecision,
    Issue,
    Metrics,
    Proposal,
    RunManifest,
    TraceStep,
    WeeklyReport,
)

__all__ = ["RunArtifacts", "read_json", "write_json", "write_run"]


@dataclass(frozen=True)
class RunArtifacts:
    """Everything a run writes, already in memory."""

    manifest: RunManifest
    input_cases: Sequence[Case]
    cases: Sequence[Case]
    traces: Mapping[str, Sequence[TraceStep]]
    extractions: Mapping[str, Extraction]
    proposals: Mapping[str, Proposal]
    decisions: Sequence[HumanDecision]
    evidence: Mapping[str, Mapping[str, object]]
    tool_outputs: Mapping[str, object]
    issues: Sequence[Issue]
    eight_d: Sequence[EightD]
    memos: Sequence[DecisionMemo]
    reports: Sequence[WeeklyReport]
    metrics_before: Metrics
    metrics_after: Metrics
    events: Sequence[ReplayEvent]
    examples: Sequence[ComparisonExample]


def write_json(path: Path, payload: Any) -> None:
    """Write indented, key-sorted JSON with one trailing newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(value: Any) -> Any:
    return value.model_dump(mode="json")


def _traces(traces: Mapping[str, Sequence[TraceStep]]) -> dict[str, object]:
    return {
        case_id: [_dump(step) for step in steps]
        for case_id, steps in sorted(traces.items())
    }


def _evidence(evidence: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    return {case_id: dict(value) for case_id, value in sorted(evidence.items())}


def _events(events: Sequence[ReplayEvent]) -> list[object]:
    return [_dump(event) for event in sorted(events, key=lambda event: event.seq)]


def write_run(directory: str | Path, artifacts: RunArtifacts) -> Path:
    """Write every documented file and return the run directory."""

    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    reports = sorted(
        artifacts.reports,
        key=lambda report: (report.week_start, report.week_end),
    )
    latest = reports[-1] if reports else None
    file_payloads: dict[str, Any] = {
        "input_cases.json": [_dump(case) for case in sorted(
            artifacts.input_cases, key=lambda case: (case.received_at, case.id)
        )],
        "cases.json": [_dump(case) for case in sorted(
            artifacts.cases, key=lambda case: (case.received_at, case.id)
        )],
        "traces.json": _traces(artifacts.traces),
        "extractions.json": {
            case_id: _dump(value)
            for case_id, value in sorted(artifacts.extractions.items())
        },
        "proposals.json": {
            case_id: _dump(value)
            for case_id, value in sorted(artifacts.proposals.items())
        },
        "decisions.json": [
            _dump(decision)
            for decision in sorted(artifacts.decisions, key=lambda item: item.case_id)
        ],
        "evidence.json": _evidence(artifacts.evidence),
        "tool_outputs.json": dict(artifacts.tool_outputs),
        "issues.json": [_dump(issue) for issue in sorted(
            artifacts.issues, key=lambda issue: (issue.opened_at, issue.id)
        )],
        "eight_d.json": [_dump(draft) for draft in sorted(
            artifacts.eight_d, key=lambda draft: draft.id
        )],
        "memos.json": [_dump(memo) for memo in sorted(
            artifacts.memos, key=lambda memo: memo.id
        )],
        "report.json": _dump(latest) if latest is not None else None,
        "reports.json": [_dump(report) for report in reports[:-1]],
        "metrics.json": {
            "before": _dump(artifacts.metrics_before),
            "after": _dump(artifacts.metrics_after),
        },
        "events.json": _events(artifacts.events),
        "comparison_examples.json": [
            _dump(example) for example in artifacts.examples
        ],
    }
    names = sorted([*file_payloads, "manifest.json"])
    manifest = artifacts.manifest.model_copy(update={"files": tuple(names)})
    file_payloads["manifest.json"] = _dump(manifest)

    for name in names:
        write_json(root / name, file_payloads[name])
    return root


def iso(value: datetime) -> str:
    """ISO 8601 UTC, as the interfaces document it."""

    return value.isoformat().replace("+00:00", "Z")
