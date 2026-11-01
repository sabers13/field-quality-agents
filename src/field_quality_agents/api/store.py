"""Read-side store for recorded runs and live overlays.

The API never runs a pipeline. It serves what a run wrote under
``results/runs/<run_id>/`` and, in live mode, the cases a live desk has touched.

A recorded run directory uses this layout (missing files mean "no data"; Q8 is
the writer):

```text
results/runs/<run_id>/
  manifest.json       RunManifest
  cases.json          list[Case] (final state)
  input_cases.json    list[Case] (as received, used to start live threads)
  traces.json         {case_id: list[TraceStep]}
  extractions.json    {case_id: Extraction}
  proposals.json      {case_id: Proposal}
  decisions.json      list[HumanDecision] or {case_id: HumanDecision}
  evidence.json       {case_id: {similar_cases: [], recalls: [], investigations: []}}
  tool_outputs.json   {case_id: {similar_cases: [], recalls: [], investigations: []}} (full rows)
  issues.json         list[Issue]
  eight_d.json        list[EightD]
  memos.json          list[DecisionMemo]
  report.json         WeeklyReport (latest)
  reports.json        list[WeeklyReport] (the other weeks)
  metrics.json        {"before": Metrics, "after": Metrics}
  events.json         list[ReplayEvent]
  comparison_examples.json  list[{case_id, before, after, note}]
```
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol, cast

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from field_quality_agents.api.models import (
    ComparisonExample,
    InvestigationRef,
    RecallRef,
    SimilarCaseRef,
)
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

__all__ = [
    "CaseEvidence",
    "CaseRecord",
    "ComparisonExample",
    "FileResultStore",
    "IssueRecord",
    "MemoryResultStore",
    "MetricsPair",
    "ReplayEventRecord",
    "ReplayRunRecord",
    "ResultStore",
    "ResultStoreError",
]

ReplayEventKind = Literal["case", "trace", "decision", "issue", "report"]


class ResultStoreError(RuntimeError):
    """A recorded run exists but cannot be read as documented."""


@dataclass(frozen=True)
class CaseRecord:
    """One case plus what the run recorded for it."""

    case: Case
    trace: tuple[TraceStep, ...] = ()
    extraction: Extraction | None = None
    proposal: Proposal | None = None
    decision: HumanDecision | None = None


@dataclass(frozen=True)
class CaseEvidence:
    """The related evidence shown beside a case."""

    similar_cases: tuple[SimilarCaseRef, ...] = ()
    recalls: tuple[RecallRef, ...] = ()
    investigations: tuple[InvestigationRef, ...] = ()


@dataclass(frozen=True)
class IssueRecord:
    issue: Issue
    eight_d: EightD | None = None
    memo: DecisionMemo | None = None


@dataclass(frozen=True)
class ReplayRunRecord:
    run_id: str
    set_name: str
    started_at: datetime
    status: Literal["running", "complete", "failed"]
    case_count: int


@dataclass(frozen=True)
class ReplayEventRecord:
    seq: int
    at: datetime
    kind: ReplayEventKind
    case_id: str | None = None
    issue_id: str | None = None
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MetricsPair:
    before: Metrics
    after: Metrics


class ResultStore(Protocol):
    """The read surface the API depends on; tests use ``MemoryResultStore``."""

    def runs(self) -> Sequence[ReplayRunRecord]: ...

    def active_run_id(self) -> str | None: ...

    def cases(self) -> Sequence[CaseRecord]: ...

    def evidence(self, case_id: str) -> CaseEvidence: ...

    def issues(self) -> Sequence[IssueRecord]: ...

    def replay_events(self, run_id: str) -> Sequence[ReplayEventRecord]: ...

    def weekly_reports(self) -> Sequence[WeeklyReport]: ...

    def metrics(self) -> MetricsPair | None: ...

    def comparison_examples(self) -> Sequence[ComparisonExample]: ...


class MemoryResultStore:
    """In-memory fixture store used by the API tests."""

    def __init__(
        self,
        *,
        cases: Sequence[CaseRecord] = (),
        evidence: Mapping[str, CaseEvidence] | None = None,
        issues: Sequence[IssueRecord] = (),
        runs: Sequence[ReplayRunRecord] = (),
        events: Mapping[str, Sequence[ReplayEventRecord]] | None = None,
        weekly_reports: Sequence[WeeklyReport] = (),
        metrics: MetricsPair | None = None,
        comparison_examples: Sequence[ComparisonExample] = (),
    ) -> None:
        self._cases = tuple(cases)
        self._evidence = dict(evidence or {})
        self._issues = tuple(issues)
        self._runs = tuple(sorted(runs, key=lambda run: (run.started_at, run.run_id), reverse=True))
        self._events = {run_id: tuple(items) for run_id, items in (events or {}).items()}
        self._reports = tuple(weekly_reports)
        self._metrics = metrics
        self._examples = tuple(comparison_examples)

    def runs(self) -> Sequence[ReplayRunRecord]:
        return self._runs

    def active_run_id(self) -> str | None:
        return self._runs[0].run_id if self._runs else None

    def cases(self) -> Sequence[CaseRecord]:
        return self._cases

    def evidence(self, case_id: str) -> CaseEvidence:
        return self._evidence.get(case_id, CaseEvidence())

    def issues(self) -> Sequence[IssueRecord]:
        return self._issues

    def replay_events(self, run_id: str) -> Sequence[ReplayEventRecord]:
        return self._events.get(run_id, ())

    def weekly_reports(self) -> Sequence[WeeklyReport]:
        return self._reports

    def metrics(self) -> MetricsPair | None:
        return self._metrics

    def comparison_examples(self) -> Sequence[ComparisonExample]:
        return self._examples


# --------------------------------------------------------------------------
# File-backed store


@dataclass(frozen=True)
class _Loaded:
    runs: tuple[ReplayRunRecord, ...] = ()
    active_run_id: str | None = None
    cases: tuple[CaseRecord, ...] = ()
    evidence: Mapping[str, CaseEvidence] = field(default_factory=dict)
    issues: tuple[IssueRecord, ...] = ()
    events: Mapping[str, tuple[ReplayEventRecord, ...]] = field(default_factory=dict)
    reports: tuple[WeeklyReport, ...] = ()
    metrics: MetricsPair | None = None
    examples: tuple[ComparisonExample, ...] = ()


class _RawEvent(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    seq: int
    at: datetime
    kind: ReplayEventKind
    case_id: str | None = None
    issue_id: str | None = None
    payload: dict[str, object] = {}


_CASES = TypeAdapter(list[Case])
_TRACES = TypeAdapter(dict[str, list[TraceStep]])
_EXTRACTIONS = TypeAdapter(dict[str, Extraction])
_PROPOSALS = TypeAdapter(dict[str, Proposal])
_DECISIONS_LIST = TypeAdapter(list[HumanDecision])
_DECISIONS_MAP = TypeAdapter(dict[str, HumanDecision])
_ISSUES = TypeAdapter(list[Issue])
_EIGHT_D = TypeAdapter(list[EightD])
_MEMOS = TypeAdapter(list[DecisionMemo])
_REPORTS = TypeAdapter(list[WeeklyReport])
_EVENTS = TypeAdapter(list[_RawEvent])
_SIMILAR = TypeAdapter(list[SimilarCaseRef])
_RECALLS = TypeAdapter(list[RecallRef])
_INVESTIGATIONS = TypeAdapter(list[InvestigationRef])
_EXAMPLES = TypeAdapter(list[ComparisonExample])
_MANIFEST = TypeAdapter(RunManifest)
_METRICS = TypeAdapter(Metrics)
_WEEKLY_REPORT = TypeAdapter(WeeklyReport)


def _read(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ResultStoreError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ResultStoreError(f"invalid JSON in {path}: {exc}") from exc


def _parse[T](adapter: TypeAdapter[T], raw: object, path: Path) -> T:
    try:
        return adapter.validate_python(raw)
    except ValidationError as exc:
        raise ResultStoreError(f"invalid recorded shape in {path}: {exc}") from exc


def _items(raw: object) -> list[object]:
    if isinstance(raw, dict):
        candidate = cast(dict[str, object], raw).get("items")
        if isinstance(candidate, list):
            return cast(list[object], candidate)
    if isinstance(raw, list):
        return cast(list[object], raw)
    return []


def _ref_fields(item: Mapping[str, object]) -> dict[str, object]:
    return {
        "id": str(item.get("id", "")),
        "summary": str(item.get("summary", "")),
        "open_date": item.get("open_date"),
        "match": bool(item.get("match", True)),
    }


def _dict_items(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    return [cast(dict[str, object], item) for item in raw if isinstance(item, dict)]


def _evidence(raw: object, path: Path) -> dict[str, CaseEvidence]:
    if not isinstance(raw, dict):
        raise ResultStoreError(f"evidence in {path} must be an object keyed by case id")
    evidence: dict[str, CaseEvidence] = {}
    for case_id, block in cast(dict[str, object], raw).items():
        if not isinstance(block, dict):
            continue
        values = cast(dict[str, object], block)
        similar = _parse(_SIMILAR, values.get("similar_cases", []), path)
        recalls = _parse(
            _RECALLS,
            [_ref_fields(item) for item in _dict_items(values.get("recalls"))],
            path,
        )
        investigations = _parse(
            _INVESTIGATIONS,
            [_ref_fields(item) for item in _dict_items(values.get("investigations"))],
            path,
        )
        evidence[str(case_id)] = CaseEvidence(
            similar_cases=tuple(similar),
            recalls=tuple(recalls),
            investigations=tuple(investigations),
        )
    return evidence


def _run_record(manifest: RunManifest, directory: Path) -> ReplayRunRecord:
    return ReplayRunRecord(
        run_id=manifest.run_id or directory.name,
        set_name=manifest.set_name,
        started_at=manifest.started_at,
        status=manifest.status.value,
        case_count=manifest.case_count,
    )


class FileResultStore:
    """Read the newest run (or a named one) from a results directory."""

    def __init__(self, root: str | Path = "results/runs", *, run_id: str | None = None) -> None:
        self._root = Path(root)
        self._requested = run_id
        self._loaded: _Loaded | None = None

    @property
    def root(self) -> Path:
        return self._root

    def runs(self) -> Sequence[ReplayRunRecord]:
        return self._load().runs

    def active_run_id(self) -> str | None:
        return self._load().active_run_id

    def cases(self) -> Sequence[CaseRecord]:
        return self._load().cases

    def evidence(self, case_id: str) -> CaseEvidence:
        return self._load().evidence.get(case_id, CaseEvidence())

    def issues(self) -> Sequence[IssueRecord]:
        return self._load().issues

    def replay_events(self, run_id: str) -> Sequence[ReplayEventRecord]:
        return self._load().events.get(run_id, ())

    def weekly_reports(self) -> Sequence[WeeklyReport]:
        return self._load().reports

    def metrics(self) -> MetricsPair | None:
        return self._load().metrics

    def comparison_examples(self) -> Sequence[ComparisonExample]:
        return self._load().examples

    # -- loading -----------------------------------------------------------

    def _load(self) -> _Loaded:
        if self._loaded is None:
            self._loaded = self._read_root()
        return self._loaded

    def _read_root(self) -> _Loaded:
        if not self._root.is_dir():
            return _Loaded()

        manifests: dict[str, tuple[ReplayRunRecord, Path]] = {}
        for directory in sorted(self._root.iterdir()):
            manifest_path = directory / "manifest.json"
            if not directory.is_dir() or not manifest_path.is_file():
                continue
            manifest = _parse(_MANIFEST, _read(manifest_path), manifest_path)
            record = _run_record(manifest, directory)
            manifests[record.run_id] = (record, directory)

        runs = tuple(
            sorted(
                (record for record, _ in manifests.values()),
                key=lambda run: (run.started_at, run.run_id),
                reverse=True,
            )
        )
        active = manifests.get(self._requested) if self._requested is not None else None
        if active is None and self._requested is None and runs:
            active = manifests[runs[0].run_id]

        if active is None:
            return _Loaded(runs=runs)

        record, directory = active
        return _Loaded(
            runs=runs,
            active_run_id=record.run_id,
            cases=self._read_cases(directory),
            evidence=self._read_evidence(directory),
            issues=self._read_issues(directory),
            events=self._read_events(directory, record.run_id),
            reports=self._read_reports(directory),
            metrics=self._read_metrics(directory),
            examples=self._read_examples(directory),
        )

    def _read_traces(self, directory: Path) -> dict[str, list[TraceStep]]:
        path = directory / "traces.json"
        if not path.is_file():
            return {}
        return _parse(_TRACES, _read(path), path)

    def _read_extractions(self, directory: Path) -> dict[str, Extraction]:
        path = directory / "extractions.json"
        if not path.is_file():
            return {}
        return _parse(_EXTRACTIONS, _read(path), path)

    def _read_proposals(self, directory: Path) -> dict[str, Proposal]:
        path = directory / "proposals.json"
        if not path.is_file():
            return {}
        return _parse(_PROPOSALS, _read(path), path)

    def _read_cases(self, directory: Path) -> tuple[CaseRecord, ...]:
        path = directory / "cases.json"
        if not path.is_file():
            return ()
        cases = _parse(_CASES, _items(_read(path)), path)
        traces = self._read_traces(directory)
        extractions = self._read_extractions(directory)
        proposals = self._read_proposals(directory)
        decisions = self._read_decisions(directory)
        return tuple(
            CaseRecord(
                case=case,
                trace=tuple(traces.get(case.id, [])),
                extraction=extractions.get(case.id),
                proposal=proposals.get(case.id),
                decision=decisions.get(case.id),
            )
            for case in cases
        )

    def _read_decisions(self, directory: Path) -> dict[str, HumanDecision]:
        path = directory / "decisions.json"
        if not path.is_file():
            return {}
        raw = _read(path)
        if isinstance(raw, list):
            decisions = _parse(_DECISIONS_LIST, raw, path)
            return {decision.case_id: decision for decision in decisions}
        return _parse(_DECISIONS_MAP, raw, path)

    def _read_evidence(self, directory: Path) -> dict[str, CaseEvidence]:
        path = directory / "evidence.json"
        if not path.is_file():
            return {}
        return _evidence(_read(path), path)

    def _read_issues(self, directory: Path) -> tuple[IssueRecord, ...]:
        path = directory / "issues.json"
        if not path.is_file():
            return ()
        issues = _parse(_ISSUES, _items(_read(path)), path)
        eight_by_id: dict[str, EightD] = {}
        eight_by_issue: dict[str, EightD] = {}
        eight_path = directory / "eight_d.json"
        if eight_path.is_file():
            for draft in _parse(_EIGHT_D, _items(_read(eight_path)), eight_path):
                eight_by_id[draft.id] = draft
                eight_by_issue[draft.issue_id] = draft
        memo_by_id: dict[str, DecisionMemo] = {}
        memo_by_issue: dict[str, DecisionMemo] = {}
        memo_path = directory / "memos.json"
        if memo_path.is_file():
            for document in _parse(_MEMOS, _items(_read(memo_path)), memo_path):
                memo_by_id[document.id] = document
                memo_by_issue[document.issue_id] = document

        records: list[IssueRecord] = []
        for issue in issues:
            eight = eight_by_id.get(issue.eight_d_id or "") or eight_by_issue.get(issue.id)
            memo = memo_by_id.get(issue.memo_id or "") or memo_by_issue.get(issue.id)
            records.append(IssueRecord(issue=issue, eight_d=eight, memo=memo))
        return tuple(records)

    def _read_events(
        self, directory: Path, run_id: str
    ) -> dict[str, tuple[ReplayEventRecord, ...]]:
        path = directory / "events.json"
        if not path.is_file():
            return {}
        events = _parse(_EVENTS, _items(_read(path)), path)
        return {
            run_id: tuple(
                ReplayEventRecord(
                    seq=event.seq,
                    at=event.at,
                    kind=event.kind,
                    case_id=event.case_id,
                    issue_id=event.issue_id,
                    payload=dict(event.payload),
                )
                for event in sorted(events, key=lambda item: item.seq)
            )
        }

    def _read_reports(self, directory: Path) -> tuple[WeeklyReport, ...]:
        reports: list[WeeklyReport] = []
        path = directory / "report.json"
        if path.is_file():
            reports.append(_parse(_WEEKLY_REPORT, _read(path), path))
        many = directory / "reports.json"
        if many.is_file():
            more = _parse(_REPORTS, _items(_read(many)), many)
            reports.extend(more)
        return tuple(reports)

    def _read_metrics(self, directory: Path) -> MetricsPair | None:
        path = directory / "metrics.json"
        if not path.is_file():
            return None
        raw = _read(path)
        if not isinstance(raw, dict):
            raise ResultStoreError(f"metrics in {path} must be an object")
        values = cast(dict[str, object], raw)
        before = values.get("before")
        after = values.get("after")
        if before is None or after is None:
            return None
        return MetricsPair(
            before=_parse(_METRICS, before, path),
            after=_parse(_METRICS, after, path),
        )

    def _read_examples(self, directory: Path) -> tuple[ComparisonExample, ...]:
        path = directory / "comparison_examples.json"
        if not path.is_file():
            return ()
        parsed = _parse(_EXAMPLES, _items(_read(path)), path)
        return tuple(parsed)
