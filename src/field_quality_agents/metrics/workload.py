"""Workload metrics: human touches, steps, cost, latency and budget hits.

The input is Q5's ``CaseRun``. The same function serves the linear pipeline
because Q3 records its four fixed stages as a synthetic trace with zero cost and
zero latency; the comparison then rests on one shape.
"""

from __future__ import annotations

from collections.abc import Sequence

from field_quality_agents.agents.state import CaseRun
from field_quality_agents.contracts import DecisionAction
from field_quality_agents.metrics.estimates import mean, percentile

__all__ = ["workload"]


def _case_duration_ms(run: CaseRun) -> float:
    return float(sum(step.duration_ms for step in run.trace))


def workload(runs: Sequence[CaseRun]) -> dict[str, float]:
    """Return the PLAN §7 workload numbers for one pipeline."""

    n = len(runs)
    if n == 0:
        return {
            "human_touches_per_case": 0.0,
            "decided_without_edits_share": 0.0,
            "steps_per_case": 0.0,
            "cost_per_1000_cases_usd": 0.0,
            "latency_p50_ms": 0.0,
            "latency_p95_ms": 0.0,
            "budget_hits": 0.0,
        }

    human_touches = sum(1 for run in runs for step in run.trace if step.agent == "human")
    decisions = [run.decision for run in runs if run.decision is not None]
    unedited = sum(
        1
        for decision in decisions
        if decision.action is DecisionAction.APPROVE and decision.edited_proposal is None
    )
    durations = [_case_duration_ms(run) for run in runs]
    total_cost = sum(step.cost_usd for run in runs for step in run.trace)

    return {
        "human_touches_per_case": human_touches / n,
        "decided_without_edits_share": unedited / len(decisions) if decisions else 0.0,
        "steps_per_case": mean([float(run.steps) for run in runs]),
        "cost_per_1000_cases_usd": total_cost / n * 1_000.0,
        "latency_p50_ms": percentile(durations, 0.50),
        "latency_p95_ms": percentile(durations, 0.95),
        "budget_hits": float(sum(1 for run in runs if run.budget_hit)),
    }
