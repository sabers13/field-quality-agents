"""KPI tiles, the before/after summary and the window rule.

Every number is computed from committed run data or the in-memory store; no
model runs here. The window ends at the latest recorded case date so a replay
of an old run stays deterministic.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import date, timedelta
from statistics import median

from field_quality_agents.api.models import (
    CommandCentreData,
    ComparisonData,
    ComparisonExample,
    ComparisonHeadline,
    ComparisonRow,
    ComparisonSummary,
    Kpi,
    StreamEvent,
    Tone,
)
from field_quality_agents.api.store import (
    CaseRecord,
    IssueRecord,
    MetricsPair,
    ResultStore,
)
from field_quality_agents.contracts import (
    DecisionAction,
    IssueStatus,
    MetricEstimate,
    Metrics,
    ProposalKind,
)
from field_quality_agents.metrics import compare

__all__ = [
    "WindowError",
    "build_command_centre",
    "build_comparison",
    "build_kpis",
    "build_summary",
    "parse_window",
]

_WINDOW = re.compile(r"^(?P<days>\d{1,4})d$")


class WindowError(ValueError):
    """``window`` is not ``<days>d`` in the supported range."""


def parse_window(window: str) -> int:
    """Turn ``30d`` into ``30``; reject anything else with a clear error."""

    match = _WINDOW.match(window.strip())
    if match is None:
        raise WindowError(f"window must look like 30d, got {window!r}")
    days = int(match.group("days"))
    if not 1 <= days <= 365:
        raise WindowError("window must be between 1d and 365d")
    return days


def _number(value: MetricEstimate | float | int | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, MetricEstimate):
        return value.value
    return float(value)


def _percent(value: float) -> float:
    return round(value * 100, 1)


def _round(value: float, digits: int = 2) -> float:
    return round(value, digits)


def _decided(records: Sequence[CaseRecord]) -> list[CaseRecord]:
    return [record for record in records if record.decision is not None]


def _approved_proposal(record: CaseRecord) -> ProposalKind | None:
    decision = record.decision
    if decision is None or decision.action not in (
        DecisionAction.APPROVE,
        DecisionAction.OVERRIDE,
    ):
        return None
    proposal = decision.edited_proposal or record.proposal
    return proposal.kind if proposal is not None else None


def _verified_evidence(record: CaseRecord) -> int:
    proposal = record.proposal
    if proposal is None:
        return 0
    return sum(1 for citation in proposal.evidence if citation.verified)


def _human_touches(record: CaseRecord) -> int:
    steps = sum(1 for step in record.trace if step.agent in ("human", "live_engineer"))
    return max(steps, 1 if record.decision is not None else 0)


def _days_to_decision(record: CaseRecord) -> int | None:
    decision = record.decision
    if decision is None:
        return None
    return max(0, (decision.decided_at.date() - record.case.received_at).days)


def _weekly_series(records: Sequence[CaseRecord], reference: date, weeks: int = 8) -> list[float]:
    end = reference - timedelta(days=reference.weekday())
    buckets = {(end - timedelta(weeks=index)): 0 for index in range(weeks)}
    for record in records:
        received = record.case.received_at
        week_start = received - timedelta(days=received.weekday())
        if week_start in buckets:
            buckets[week_start] += 1
    return [float(buckets[end - timedelta(weeks=index)]) for index in range(weeks - 1, -1, -1)]


def _ntf_without_evidence(records: Sequence[CaseRecord]) -> float:
    decided = _decided(records)
    if not decided:
        return 0.0
    flagged = sum(
        1
        for record in decided
        if _approved_proposal(record) is ProposalKind.STANDARD_TEST
        and _verified_evidence(record) == 0
    )
    return flagged / len(decided)


def _tone_for_share(share: float) -> Tone:
    if share >= 0.2:
        return "issue"
    if share > 0:
        return "watch"
    return "good"


def build_kpis(
    *,
    records: Sequence[CaseRecord],
    all_records: Sequence[CaseRecord],
    issues: Sequence[IssueRecord],
    pair: MetricsPair | None,
    reference: date,
    days: int,
) -> list[Kpi]:
    """The seven PLAN §6 tiles for the window ending at ``reference``."""

    start = reference - timedelta(days=days)
    window = [record for record in records if record.case.received_at > start]
    previous_start = start - timedelta(days=days)
    previous = [
        record for record in all_records if previous_start < record.case.received_at <= start
    ]

    decided = _decided(window)
    decided_without_edits = sum(
        1
        for record in decided
        if record.decision is not None
        and record.decision.action is DecisionAction.APPROVE
        and record.decision.edited_proposal is None
    )
    touches = [_human_touches(record) for record in window]
    times = [days_to for record in decided if (days_to := _days_to_decision(record)) is not None]
    open_issues = sum(1 for record in issues if record.issue.status is IssueStatus.OPEN)
    ntf_share = _ntf_without_evidence(window)

    after: Metrics | None = pair.after if pair is not None else None
    if after is not None and after.decided_without_edits_share is not None:
        prepared_share = after.decided_without_edits_share
    else:
        prepared_share = decided_without_edits / len(decided) if decided else 0.0
    if after is not None and after.human_touches_per_case is not None:
        human_touches = after.human_touches_per_case
    else:
        human_touches = sum(touches) / len(touches) if touches else 0.0
    cost_per_case = (
        after.cost_per_1000_cases_usd / 1000
        if after is not None and after.cost_per_1000_cases_usd is not None
        else 0.0
    )

    return [
        Kpi(
            id="cases_in",
            label="Cases in",
            value=len(window),
            unit="cases",
            context=f"received in the last {days} days",
            delta=float(len(window) - len(previous)),
            tone="neutral",
            series=_weekly_series(all_records, reference),
        ),
        Kpi(
            id="prepared_without_edits",
            label="Prepared without human edits",
            value=_percent(prepared_share),
            unit="%",
            context="share of decisions approved as proposed",
            tone="good" if prepared_share >= 0.8 else "watch",
        ),
        Kpi(
            id="human_touches",
            label="Human touches per case",
            value=_round(human_touches, 2),
            unit="per case",
            context="approve, override and ask actions per case",
            tone="neutral",
        ),
        Kpi(
            id="time_to_decision",
            label="Time to decision",
            value=_round(float(median(times)), 1) if times else 0.0,
            unit="days",
            context="median from receipt to the human decision",
            tone="neutral",
        ),
        Kpi(
            id="open_issues",
            label="Open issues",
            value=open_issues,
            unit="open",
            context="fleet issues still open",
            tone="watch" if open_issues else "good",
        ),
        Kpi(
            id="cost_per_case",
            label="Cost per case",
            value=_round(cost_per_case, 4),
            unit="USD",
            context="model spend over the recorded run",
            tone="neutral",
        ),
        Kpi(
            id="ntf_without_evidence",
            label="Standard test without evidence",
            value=_percent(ntf_share),
            unit="%",
            context="approved standard tests with no verified quote",
            tone=_tone_for_share(ntf_share),
        ),
    ]


def _headline(
    metric: str, label: str, unit: str, pair: MetricsPair
) -> ComparisonHeadline | None:
    before = _number(getattr(pair.before, metric))
    after = _number(getattr(pair.after, metric))
    if before is None or after is None:
        return None
    return ComparisonHeadline(
        id=metric,
        label=label,
        before=_round(before, 4),
        after=_round(after, 4),
        unit=unit,
    )


def build_summary(
    pair: MetricsPair | None,
    examples: Sequence[ComparisonExample] = (),
) -> ComparisonSummary:
    """The four headline pairs plus the chosen showcase examples."""

    headline: list[ComparisonHeadline] = []
    if pair is not None:
        wanted = (
            ("human_touches_per_case", "Human touches per case", "per case"),
            ("targeted_test_share", "Targeted test share", "share"),
            ("quote_grounding_rate", "Quote grounding", "share"),
            ("cost_per_1000_cases_usd", "Cost per 1,000 cases", "USD"),
        )
        for metric, label, unit in wanted:
            row = _headline(metric, label, unit, pair)
            if row is not None:
                headline.append(row)
    return ComparisonSummary(
        headline=headline,
        examples=list(examples)[:5],
    )


def build_comparison(
    pair: MetricsPair | None,
    examples: Sequence[ComparisonExample] = (),
) -> ComparisonData | None:
    """Every PLAN §7 row side by side, or ``None`` when nothing was recorded."""

    if pair is None:
        return None
    comparison = compare(pair.before, pair.after)
    rows = [
        ComparisonRow(
            metric=row.metric,
            label=row.label,
            before=row.before,
            after=row.after,
            note=row.note,
        )
        for row in comparison.rows
    ]
    return ComparisonData(
        before=pair.before,
        after=pair.after,
        summary=build_summary(pair, examples),
        rows=rows,
    )


def build_command_centre(
    *,
    store: ResultStore,
    window: str,
    feed: Sequence[StreamEvent] = (),
) -> CommandCentreData:
    days = parse_window(window)
    records = list(store.cases())
    issues = list(store.issues())
    pair = store.metrics()
    reference = max((record.case.received_at for record in records), default=date.today())
    kpis = build_kpis(
        records=records,
        all_records=records,
        issues=issues,
        pair=pair,
        reference=reference,
        days=days,
    )
    return CommandCentreData(
        window=window,
        kpis=kpis,
        live_feed=list(feed),
        comparison=build_summary(pair, store.comparison_examples()),
    )
