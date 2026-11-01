"""The end-to-end replay/record pipeline.

``fqa run`` plays the selected case set in received-date order. After each
simulated day the issue agent reviews the fleet; after each simulated week the
report agent writes the weekly report. The run writes every artifact the
dashboard reads under ``results/runs/<run_id>/``.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import cast

from field_quality_agents import __version__
from field_quality_agents.agents.graph import build_desk_graph, run_case
from field_quality_agents.agents.issue import review_day
from field_quality_agents.agents.model import AgentModel
from field_quality_agents.agents.report import build_weekly_report, week_bounds
from field_quality_agents.agents.state import (
    PROMPT_VERSION,
    CaseRun,
    use_clock,
)
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
    RunMode,
    RunStatus,
    TraceStep,
    WeeklyReport,
)
from field_quality_agents.llm.langchain_model import LangChainChatModel
from field_quality_agents.llm.prices import DEFAULT_MODEL
from field_quality_agents.llm.recorder import RecordReplayStore
from field_quality_agents.metrics import Event
from field_quality_agents.metrics.evidence import SourceIndex
from field_quality_agents.run.data import RunSource
from field_quality_agents.run.metrics import DEFAULT_SEED, compute_metrics
from field_quality_agents.run.tools import RecordingTools, ToolboxIssueTools
from field_quality_agents.run.writer import RunArtifacts, write_run

__all__ = [
    "DEFAULT_RUN_ID",
    "RunSummary",
    "build_model",
    "execute_run",
    "recordings_digest",
]

DEFAULT_RUN_ID = "replay"


@dataclass(frozen=True)
class RunSummary:
    """What ``fqa run`` prints and what the caller can assert."""

    run_id: str
    directory: Path
    cases: int
    issues: int
    reports: int
    spend_usd: float
    steps: int
    budget_hits: int
    record_digest: str


class SimulatedClock:
    """A monotonic clock with one-second steps, reset for each simulated day."""

    def __init__(self, start: datetime, step_seconds: int = 1) -> None:
        self._current = start
        self._step = timedelta(seconds=step_seconds)

    def __call__(self) -> datetime:
        now = self._current
        self._current += self._step
        return now


def build_model(*, mode: RunMode, recordings_dir: Path) -> AgentModel:
    """Build the record/replay chat model for a run."""

    from field_quality_agents.llm.budget import BudgetConfig

    request = BudgetConfig.load().request
    if mode is RunMode.REPLAY:
        store = RecordReplayStore(recordings_dir, "replay")
        return LangChainChatModel(
            store=store,
            model=DEFAULT_MODEL,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    if mode is RunMode.RECORD:
        store = RecordReplayStore(recordings_dir, "record")
        return LangChainChatModel(
            store=store,
            model=DEFAULT_MODEL,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    raise ValueError("a batch run supports replay or record mode, not live")


def _recording_hashes(root: Path) -> list[tuple[str, str]]:
    if not root.is_dir():
        return []
    hashes: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*.json")):
        hashes.append(
            (
                path.relative_to(root).as_posix(),
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    return hashes


def recordings_digest(root: Path) -> str:
    """Hash the recording set so a manifest names the bytes it replayed."""

    body = "\n".join(f"{name} {digest}" for name, digest in _recording_hashes(root))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def _source_index(
    cases: Sequence[Case],
    recalls: Mapping[str, str],
    investigations: Mapping[str, str],
) -> SourceIndex:
    return SourceIndex(
        cases={case.id: case.narrative for case in cases},
        recalls=dict(recalls),
        investigations=dict(investigations),
    )


def _day_cases(cases: Sequence[Case]) -> dict[date, list[Case]]:
    by_day: dict[date, list[Case]] = defaultdict(list)
    for case in cases:
        by_day[case.received_at].append(case)
    for day in by_day:
        by_day[day].sort(key=lambda case: case.id)
    return by_day


def _case_event(seq: int, at: datetime, run: CaseRun) -> ReplayEvent:
    return ReplayEvent(
        seq=seq,
        at=at,
        kind="case",
        case_id=run.case.id,
        payload={"status": run.case.status.value},
    )


def _trace_events(seq: int, at: datetime, run: CaseRun) -> tuple[list[ReplayEvent], int]:
    events: list[ReplayEvent] = []
    for step in run.trace:
        seq += 1
        events.append(
            ReplayEvent(
                seq=seq,
                at=at,
                kind="trace",
                case_id=run.case.id,
                payload={"step": step.model_dump(mode="json")},
            )
        )
    return events, seq


def _decision_event(
    seq: int, at: datetime, run: CaseRun, decision: HumanDecision
) -> ReplayEvent:
    return ReplayEvent(
        seq=seq,
        at=at,
        kind="decision",
        case_id=run.case.id,
        payload={
            "status": run.case.status.value,
            "action": decision.action.value,
            "actor": decision.actor.value,
        },
    )


def _issue_event(seq: int, at: datetime, issue: Issue) -> ReplayEvent:
    return ReplayEvent(
        seq=seq,
        at=at,
        kind="issue",
        issue_id=issue.id,
        payload={"status": issue.status.value, "title": issue.title},
    )


def _report_event(seq: int, report: WeeklyReport, run_id: str) -> ReplayEvent:
    return ReplayEvent(
        seq=seq,
        at=report.generated_at,
        kind="report",
        payload={
            "run_id": run_id,
            "week_start": report.week_start.isoformat(),
            "week_end": report.week_end.isoformat(),
        },
    )


def _examples(
    *,
    runs: Sequence[CaseRun],
    issues: Sequence[Issue],
    baseline_decisions: Mapping[str, dict[str, object]],
) -> list[ComparisonExample]:
    """Pick fixed showcase examples from the run's own records."""

    examples: list[ComparisonExample] = []
    ordered_runs = sorted(runs, key=lambda run: (run.case.received_at, run.case.id))
    if issues:
        issue = sorted(issues, key=lambda item: (item.opened_at, item.id))[0]
        linked = issue.linked_case_ids[0] if issue.linked_case_ids else ""
        examples.append(
            ComparisonExample(
                case_id=linked,
                before="The linear pipeline has no fleet-level issue step.",
                after=f"The issue agent opened {issue.id} on {issue.opened_at.isoformat()}.",
                note="The earliest issue in the run.",
            )
        )
    targeted = [
        run
        for run in ordered_runs
        if run.proposal is not None
        and run.proposal.kind.value == "targeted_load_test"
    ]
    if targeted:
        longest = max(targeted, key=lambda run: (len(run.trace), run.case.id))
        examples.append(
            ComparisonExample(
                case_id=longest.case.id,
                before="Standard test; the simulation always passes.",
                after=f"Targeted test requested after {len(longest.trace)} trace steps.",
                note="The longest agent trace that ended in a targeted test.",
            )
        )
    for run in ordered_runs:
        baseline = baseline_decisions.get(run.case.id)
        if baseline is None:
            continue
        if not baseline.get("closed_no_trouble_found"):
            continue
        if run.proposal is None or not run.proposal.evidence:
            continue
        examples.append(
            ComparisonExample(
                case_id=run.case.id,
                before="Closed as no trouble found.",
                after="The agent found verified evidence and proposed a test.",
                note="Where the linear pipeline missed what the agent found.",
            )
        )
        break
    for run in ordered_runs:
        baseline = baseline_decisions.get(run.case.id)
        if baseline is None:
            continue
        if baseline.get("closed_no_trouble_found") and (
            run.proposal is None or not run.proposal.evidence
        ):
            examples.append(
                ComparisonExample(
                    case_id=run.case.id,
                    before="Closed as no trouble found with the keyword rules.",
                    after="The agent also found no verified evidence.",
                    note="Where the linear pipeline was right.",
                )
            )
            break
    return examples[:5]


def _load_baseline_metrics(path: Path) -> Metrics:
    if not path.is_file():
        return Metrics()
    import json

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Metrics()
    try:
        return Metrics.model_validate(raw)
    except Exception:
        return Metrics()


def _load_baseline_decisions(path: Path) -> dict[str, dict[str, object]]:
    if not path.is_file():
        return {}
    import json

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, list):
        return {}
    decisions: dict[str, dict[str, object]] = {}
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("case_id"), str):
            decisions[str(item["case_id"])] = cast(dict[str, object], item)
    return decisions


def execute_run(
    *,
    source: RunSource,
    recordings_dir: Path,
    results_dir: Path,
    run_id: str,
    set_name: str,
    mode: RunMode,
    model: AgentModel | None = None,
    model_name: str = DEFAULT_MODEL,
    seed: int = DEFAULT_SEED,
    baseline_dir: Path = Path("results/baseline"),
    limit: int | None = None,
) -> RunSummary:
    """Play one set through the desk and write the run directory.

    ``limit`` keeps the first N cases in received-date order. Q9's smoke run
    uses it to check the live traces before paying for the full set; the
    recordings it leaves behind replay in the full run.
    """

    cases = source.cases()
    if not cases:
        raise ValueError("the selected case set is empty")
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        cases = cases[:limit]
    day_cases = _day_cases(cases)
    first_day = min(day_cases)
    last_day = max(day_cases)
    recordings = recordings_dir.resolve()
    agent_model = model if model is not None else build_model(
        mode=mode, recordings_dir=recordings
    )
    recording_tools = RecordingTools(source.toolbox)
    graph = build_desk_graph(tools=recording_tools, model=agent_model)
    issue_tools = ToolboxIssueTools(source.toolbox)
    event_truth = source.events()
    recall_text, investigation_text = source.event_texts()

    runs_by_case: dict[str, CaseRun] = {}
    traces: dict[str, tuple[TraceStep, ...]] = {}
    extractions: dict[str, Extraction] = {}
    proposals: dict[str, Proposal] = {}
    decisions: list[HumanDecision] = []
    seen: list[Case] = []
    issues: list[Issue] = []
    eight_d: list[EightD] = []
    memos: list[DecisionMemo] = []
    reports: list[WeeklyReport] = []
    events: list[ReplayEvent] = []
    seq = 0

    week_cursor = week_bounds(first_day)[0]
    while week_cursor <= last_day:
        week_end = date.fromordinal(week_cursor.toordinal() + 6)
        day_cursor = week_cursor
        while day_cursor <= min(week_end, last_day):
            today = day_cases.get(day_cursor, [])
            if today:
                clock = SimulatedClock(
                    datetime.combine(day_cursor, time(7, 0), tzinfo=UTC)
                )
                with use_clock(clock):
                    for case in today:
                        recording_tools.current_case_id = case.id
                        run = run_case(case, graph)
                        runs_by_case[case.id] = run
                        traces[case.id] = run.trace
                        if run.extraction is not None:
                            extractions[case.id] = run.extraction
                        if run.proposal is not None:
                            proposals[case.id] = run.proposal
                        if run.decision is not None:
                            decisions.append(run.decision)
                        seen.append(case)
                        if run.pending:
                            raise RuntimeError(
                                f"{case.id} is still waiting for a human decision"
                            )
                        seq += 1
                        events.append(_case_event(seq, clock(), run))
                        trace_events, seq = _trace_events(seq, clock(), run)
                        events.extend(trace_events)
                        if run.decision is not None:
                            seq += 1
                            events.append(
                                _decision_event(seq, clock(), run, run.decision)
                            )

                issue_clock = SimulatedClock(
                    datetime.combine(day_cursor, time(18, 0), tzinfo=UTC)
                )
                with use_clock(issue_clock):
                    result = review_day(
                        cases=seen,
                        until=day_cursor,
                        tools=issue_tools,
                        existing_issues=issues,
                    )
                    for draft in result.drafts:
                        issues.append(draft.issue)
                        eight_d.append(draft.eight_d)
                        memos.append(draft.memo)
                        seq += 1
                        events.append(
                            _issue_event(seq, issue_clock(), draft.issue)
                        )
            day_cursor = date.fromordinal(day_cursor.toordinal() + 1)

        report = _report_for_week(
            week_start=week_cursor,
            week_end=week_end,
            cases=cases,
            runs_by_case=runs_by_case,
            proposals=proposals,
            issues=issues,
            eight_d=eight_d,
            memos=memos,
            sources=_source_index(cases, recall_text, investigation_text),
            events=event_truth,
            seed=seed,
        )
        reports.append(report)
        seq += 1
        events.append(_report_event(seq, report, run_id))
        week_cursor = date.fromordinal(week_cursor.toordinal() + 7)

    if not reports:
        raise RuntimeError("the run produced no weekly report")

    ordered_runs = [runs_by_case[case.id] for case in cases if case.id in runs_by_case]
    all_evidence = {
        case.id: recording_tools.outputs(case.id).evidence()
        for case in cases
        if case.id in runs_by_case
    }
    final_sources = _source_index(cases, recall_text, investigation_text)
    metrics_after = compute_metrics(
        runs=ordered_runs,
        truth_cases=cases,
        proposals=list(proposals.values()),
        issues=issues,
        eight_d=eight_d,
        memos=memos,
        sources=final_sources,
        events=event_truth,
        seed=seed,
    )
    metrics_before = _load_baseline_metrics(baseline_dir / "metrics.json")
    baseline_decisions = _load_baseline_decisions(baseline_dir / "decisions.json")
    examples = _examples(
        runs=ordered_runs,
        issues=issues,
        baseline_decisions=baseline_decisions,
    )
    spend = sum(step.cost_usd for run in ordered_runs for step in run.trace)
    steps = sum(run.steps for run in ordered_runs)
    budget_hits = sum(1 for run in ordered_runs if run.budget_hit)
    started_at = datetime.combine(first_day, time(6, 0), tzinfo=UTC)
    completed_at = datetime.combine(last_day, time(23, 59), tzinfo=UTC)
    directory = results_dir / run_id
    manifest = RunManifest(
        run_id=run_id,
        mode=mode,
        set_name=set_name,
        started_at=started_at,
        completed_at=completed_at,
        status=RunStatus.COMPLETE,
        case_count=len(cases),
        model=model_name,
        prompt_version=PROMPT_VERSION,
        seed=seed,
        spend_usd=round(spend, 6),
        steps=steps,
        budget_hits=budget_hits,
        record_digest=recordings_digest(recordings),
        code_version=__version__,
    )
    artifacts = RunArtifacts(
        manifest=manifest,
        input_cases=cases,
        cases=[runs_by_case[case.id].case for case in cases if case.id in runs_by_case],
        traces=traces,
        extractions=extractions,
        proposals=proposals,
        decisions=decisions,
        evidence=all_evidence,
        tool_outputs=recording_tools.all_outputs(),
        issues=issues,
        eight_d=eight_d,
        memos=memos,
        reports=reports,
        metrics_before=metrics_before,
        metrics_after=metrics_after,
        events=events,
        examples=examples,
    )
    write_run(directory, artifacts)
    return RunSummary(
        run_id=run_id,
        directory=directory,
        cases=len(cases),
        issues=len(issues),
        reports=len(reports),
        spend_usd=manifest.spend_usd,
        steps=steps,
        budget_hits=budget_hits,
        record_digest=manifest.record_digest,
    )


def _report_for_week(
    *,
    week_start: date,
    week_end: date,
    cases: Sequence[Case],
    runs_by_case: Mapping[str, CaseRun],
    proposals: Mapping[str, Proposal],
    issues: Sequence[Issue],
    eight_d: Sequence[EightD],
    memos: Sequence[DecisionMemo],
    sources: SourceIndex,
    events: Sequence[Event],
    seed: int,
) -> WeeklyReport:
    week_cases = [
        case for case in cases if week_start <= case.received_at <= week_end
    ]
    week_runs = [runs_by_case[case.id] for case in week_cases if case.id in runs_by_case]
    week_proposals = [
        proposals[case.id] for case in week_cases if case.id in proposals
    ]
    week_issue_ids = {
        issue.id
        for issue in issues
        if week_start <= issue.opened_at <= week_end
    }
    week_issues = [issue for issue in issues if issue.id in week_issue_ids]
    week_eight = [draft for draft in eight_d if draft.issue_id in week_issue_ids]
    week_memos = [memo for memo in memos if memo.issue_id in week_issue_ids]
    week_metrics = compute_metrics(
        runs=week_runs,
        truth_cases=week_cases,
        proposals=week_proposals,
        issues=week_issues,
        eight_d=week_eight,
        memos=week_memos,
        sources=sources,
        events=events,
        seed=seed,
    )
    return build_weekly_report(
        week_start=week_start,
        week_end=week_end,
        runs=list(runs_by_case.values()),
        proposals=list(proposals.values()),
        issues=list(issues),
        metrics=week_metrics,
        generated_at=datetime.combine(week_end, time(23, 59), tzinfo=UTC),
    )
