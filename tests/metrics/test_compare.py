"""The before/after comparison keeps both pipelines on identical rows."""

from __future__ import annotations

from field_quality_agents.contracts import MetricEstimate, Metrics
from field_quality_agents.metrics import compare


def test_compare_builds_every_row_in_fixed_order() -> None:
    before = Metrics(
        cases=10,
        group_macro_f1=MetricEstimate(value=0.5, ci_low=0.4, ci_high=0.6, n=10),
        human_touches_per_case=1.0,
        cost_per_1000_cases_usd=0.0,
        budget_hits=0,
    )
    after = Metrics(
        cases=10,
        group_macro_f1=MetricEstimate(value=0.7, ci_low=0.6, ci_high=0.8, n=10),
        human_touches_per_case=0.5,
        cost_per_1000_cases_usd=2.5,
        budget_hits=1,
    )

    result = compare(before, after)

    assert result.before is before
    assert result.after is after
    assert len(result.rows) == 19
    assert [row.metric for row in result.rows[:3]] == [
        "group_macro_f1",
        "group_coverage",
        "safety_precision",
    ]

    by_metric = {row.metric: row for row in result.rows}
    assert by_metric["group_macro_f1"].delta == 0.2
    assert by_metric["human_touches_per_case"].delta == -0.5
    assert by_metric["cost_per_1000_cases_usd"].delta == 2.5
    assert by_metric["budget_hits"].delta == 1.0
    assert by_metric["group_macro_f1"].before == before.group_macro_f1


def test_missing_values_produce_no_delta() -> None:
    result = compare(Metrics(), Metrics())
    by_metric = {row.metric: row for row in result.rows}
    assert by_metric["group_macro_f1"].delta is None
    assert by_metric["issue_precision"].delta is None
    # budget_hits is a plain counter with a default of 0, so its delta is 0.
    assert by_metric["budget_hits"].delta == 0.0
