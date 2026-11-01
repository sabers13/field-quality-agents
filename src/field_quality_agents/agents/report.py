"""Report agent: the weekly quality report, counted from the run's own tables.

PLAN §4 asks for volumes, decisions, open issues and KPIs. Every number here is
counted from the ``CaseRun``, ``Proposal`` and ``Issue`` records the run already
holds; the agent never estimates a figure and never asks a model to grade the
run.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from field_quality_agents.agents.state import CaseRun
from field_quality_agents.contracts import (
    CaseStatus,
    Issue,
    IssueStatus,
    Metrics,
    Proposal,
    ProposalKind,
    WeeklyReport,
)

__all__ = ["build_weekly_report", "week_bounds"]


def week_bounds(day: date) -> tuple[date, date]:
    """Return the Monday and Sunday of the week containing ``day``."""

    start = date.fromordinal(day.toordinal() - day.weekday())
    return start, date.fromordinal(start.toordinal() + 6)


def _in_week(value: date, start: date, end: date) -> bool:
    return start <= value <= end


def _decision_day(run: CaseRun) -> date | None:
    if run.decision is None:
        return None
    return run.decision.decided_at.date()


def build_weekly_report(
    *,
    week_start: date,
    week_end: date,
    runs: Sequence[CaseRun],
    proposals: Sequence[Proposal],
    issues: Sequence[Issue],
    metrics: Metrics,
    generated_at: datetime,
) -> WeeklyReport:
    """Build one weekly report from the records produced so far."""

    week_runs = [run for run in runs if _in_week(run.case.received_at, week_start, week_end)]
    decided = [
        run
        for run in week_runs
        if (day := _decision_day(run)) is not None and _in_week(day, week_start, week_end)
    ]
    needing = [
        run for run in week_runs if run.case.status is CaseStatus.NEEDS_ENGINEER
    ]
    open_issues = [
        issue
        for issue in issues
        if issue.opened_at <= week_end and issue.status is IssueStatus.OPEN
    ]
    targeted = [
        proposal
        for proposal in proposals
        if _in_week(proposal.created_at.date(), week_start, week_end)
        and proposal.kind is ProposalKind.TARGETED_LOAD_TEST
    ]
    received = len(week_runs)
    decided_count = len(decided)
    needing_count = len(needing)
    issue_count = len(open_issues)

    narrative_lines = [
        f"{received} report{'s' if received != 1 else ''} arrived in the week of "
        f"{week_start.isoformat()}; {decided_count} case"
        f"{'s' if decided_count != 1 else ''} were decided and {needing_count} "
        f"still need an engineer.",
        f"{issue_count} fleet issue{'s' if issue_count != 1 else ''} "
        f"{'were' if issue_count != 1 else 'was'} open at the end of "
        f"{week_end.isoformat()}; {len(targeted)} proposal"
        f"{'s' if len(targeted) != 1 else ''} asked for a targeted load test.",
        "Every figure is counted from the run's own case, proposal, decision and "
        "issue tables.",
    ]
    if metrics.issue_base_rate is not None and metrics.issue_precision is not None:
        narrative_lines.append(
            f"Recorded issue precision is {metrics.issue_precision.value:.4f} "
            f"against a random-week base rate of {metrics.issue_base_rate:.4f}."
        )

    return WeeklyReport(
        week_start=week_start,
        week_end=week_end,
        generated_at=generated_at,
        cases_received=received,
        cases_decided=decided_count,
        cases_needing_engineer=needing_count,
        open_issues=issue_count,
        proposals_targeted_test=len(targeted),
        metrics=metrics,
        narrative="\n\n".join(narrative_lines),
    )
