"""Side-by-side comparison of the linear and agentic metrics.

The dashboard's before/after page reads the same rows; nothing here knows
which pipeline is which beyond the two ``Metrics`` objects it is given.
"""

from __future__ import annotations

from dataclasses import dataclass

from field_quality_agents.contracts import MetricEstimate, Metrics

__all__ = ["Comparison", "ComparisonRow", "compare"]

MetricValue = MetricEstimate | float | int | None


@dataclass(frozen=True)
class ComparisonRow:
    metric: str
    label: str
    before: MetricValue
    after: MetricValue
    delta: float | None
    note: str = ""


@dataclass(frozen=True)
class Comparison:
    before: Metrics
    after: Metrics
    rows: tuple[ComparisonRow, ...]


def _number(value: MetricValue) -> float | None:
    if value is None:
        return None
    if isinstance(value, MetricEstimate):
        return value.value
    return float(value)


def _row(
    metric: str,
    label: str,
    before: MetricValue,
    after: MetricValue,
    *,
    note: str = "",
) -> ComparisonRow:
    before_number = _number(before)
    after_number = _number(after)
    delta = None
    if before_number is not None and after_number is not None:
        delta = round(after_number - before_number, 6)
    return ComparisonRow(
        metric=metric,
        label=label,
        before=before,
        after=after,
        delta=delta,
        note=note,
    )


def _note_if_missing(note: str, after: MetricValue) -> str:
    """Say why a row is blank instead of implying the agentic side scored zero."""

    if after is None:
        return "withheld: the recorded requests carried this NHTSA label"
    return note


def compare(before: Metrics, after: Metrics) -> Comparison:
    """Build every PLAN §7 comparison row in a fixed order."""

    rows = (
        _row(
            "group_macro_f1",
            "Component group macro-F1",
            before.group_macro_f1,
            after.group_macro_f1,
            note=_note_if_missing(
                "higher is better; unclear counts as wrong", after.group_macro_f1
            ),
        ),
        _row(
            "group_coverage",
            "Component group coverage",
            before.group_coverage,
            after.group_coverage,
            note=_note_if_missing("higher is better", after.group_coverage),
        ),
        _row(
            "safety_precision",
            "Safety precision",
            before.safety_precision,
            after.safety_precision,
            note=_note_if_missing("higher is better", after.safety_precision),
        ),
        _row(
            "safety_recall",
            "Safety recall",
            before.safety_recall,
            after.safety_recall,
            note=_note_if_missing("higher is better", after.safety_recall),
        ),
        _row(
            "quote_grounding_rate",
            "Quote grounding",
            before.quote_grounding_rate,
            after.quote_grounding_rate,
            note="higher is better; agentic evidence only",
        ),
        _row(
            "citation_validity_rate",
            "Citation validity",
            before.citation_validity_rate,
            after.citation_validity_rate,
            note="higher is better; agentic evidence only",
        ),
        _row(
            "targeted_test_share",
            "Targeted test share",
            before.targeted_test_share,
            after.targeted_test_share,
            note="behaviour, no ground truth",
        ),
        _row(
            "targeted_test_with_quote_share",
            "Targeted test with verified quote",
            before.targeted_test_with_quote_share,
            after.targeted_test_with_quote_share,
            note="higher is better",
        ),
        _row(
            "issue_precision",
            "Issue early share",
            before.issue_precision,
            after.issue_precision,
            note="higher is better",
        ),
        _row(
            "issue_median_lead_days",
            "Issue median lead days",
            before.issue_median_lead_days,
            after.issue_median_lead_days,
            note="higher is better",
        ),
        _row(
            "issue_base_rate",
            "Issue random-week base rate",
            before.issue_base_rate,
            after.issue_base_rate,
            note="reference line, not a score",
        ),
        _row(
            "recall_link_match_rate",
            "Recall link match rate",
            before.recall_link_match_rate,
            after.recall_link_match_rate,
            note="higher is better",
        ),
        _row(
            "human_touches_per_case",
            "Human touches per case",
            before.human_touches_per_case,
            after.human_touches_per_case,
            note="lower is better",
        ),
        _row(
            "decided_without_edits_share",
            "Decided without edits",
            before.decided_without_edits_share,
            after.decided_without_edits_share,
            note="higher is better",
        ),
        _row(
            "steps_per_case",
            "Steps per case",
            before.steps_per_case,
            after.steps_per_case,
            note="lower is better",
        ),
        _row(
            "cost_per_1000_cases_usd",
            "Cost per 1,000 cases (USD)",
            before.cost_per_1000_cases_usd,
            after.cost_per_1000_cases_usd,
            note="lower is better",
        ),
        _row(
            "latency_p50_ms",
            "Latency p50 (ms)",
            before.latency_p50_ms,
            after.latency_p50_ms,
            note="lower is better",
        ),
        _row(
            "latency_p95_ms",
            "Latency p95 (ms)",
            before.latency_p95_ms,
            after.latency_p95_ms,
            note="lower is better",
        ),
        _row(
            "budget_hits",
            "Budget hits",
            before.budget_hits,
            after.budget_hits,
            note="lower is better",
        ),
    )
    return Comparison(before=before, after=after, rows=rows)
