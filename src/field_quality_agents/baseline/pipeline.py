"""The linear "before" pipeline: register, sort, flag, test, close.

The pipeline is deliberately simple and deterministic:

1. the incoming ``Case`` is already registered;
2. ``config/keywords.toml`` sorts it to a component group;
3. the same rules raise a safety flag;
4. safety routes to ``priority``; everything else gets a ``standard_test``;
5. the standard test is simulated as passing, so every standard-test case
   closes as "no trouble found". With no clues, passing is the realistic
   default, and it is the behaviour this project compares against.

Nothing here reads ``case.group`` or ``case.safety_relevant``: those are the
NHTSA truth used by the metrics, not inputs to the baseline.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Literal

from field_quality_agents.agents.state import CaseRun
from field_quality_agents.baseline.keywords import KeywordRules, safety_flag, sort_component
from field_quality_agents.contracts import Case, TraceStep

__all__ = [
    "BaselineDecision",
    "baseline_runs",
    "run_linear",
]

Route = Literal["priority", "standard_test"]


@dataclass(frozen=True)
class BaselineDecision:
    """One case's trip through the linear pipeline."""

    case_id: str
    group: str
    safety_relevant: bool
    route: Route
    closed_no_trouble_found: bool
    keywords: tuple[str, ...]


def run_linear(
    cases: Sequence[Case],
    keywords: KeywordRules,
) -> list[BaselineDecision]:
    """Run every registered case through the fixed linear sequence."""

    decisions: list[BaselineDecision] = []
    for case in cases:
        match = sort_component(case.component, case.narrative, keywords)
        safety = safety_flag(case.component, case.narrative, keywords)
        route: Route = "priority" if safety.safety_relevant else "standard_test"
        decisions.append(
            BaselineDecision(
                case_id=case.id,
                group=match.group,
                safety_relevant=safety.safety_relevant,
                route=route,
                closed_no_trouble_found=route == "standard_test",
                keywords=match.keywords + safety.keywords,
            )
        )
    return decisions


def _trace(case: Case, decision: BaselineDecision) -> tuple[TraceStep, ...]:
    """A four-step synthetic trace so workload uses one shape for both lanes.

    The registration step is the single human touch the linear pipeline is
    modelled with: a person registers the report and pushes it to the standard
    test. The other three steps are the fixed sequence, with no model cost and
    no latency because the baseline makes no calls.
    """

    start = datetime.combine(case.received_at, time(9, 0), tzinfo=UTC)
    steps = (
        ("human", "register", "Register the report and release it to the standard path."),
        (
            "keyword",
            "sort_component",
            f"Keyword sort -> {decision.group} ({', '.join(decision.keywords) or 'no match'}).",
        ),
        (
            "test",
            "standard_test",
            "Run the standard test; the simulation always passes.",
        ),
        (
            "close",
            "close_no_trouble_found",
            "Standard test passed, so close as no trouble found."
            if decision.closed_no_trouble_found
            else "Safety priority; the case waits for an engineer instead of closing.",
        ),
    )
    return tuple(
        TraceStep(
            step=index,
            agent=agent,
            action=action,
            reason=reason,
            started_at=start + timedelta(seconds=index),
        )
        for index, (agent, action, reason) in enumerate(steps, start=1)
    )


def baseline_runs(
    cases: Sequence[Case],
    decisions: Sequence[BaselineDecision],
) -> tuple[CaseRun, ...]:
    """Wrap decisions as ``CaseRun`` records for the shared workload metric."""

    by_id = {decision.case_id: decision for decision in decisions}
    runs: list[CaseRun] = []
    for case in cases:
        decision = by_id.get(case.id)
        if decision is None:
            continue
        trace = _trace(case, decision)
        runs.append(
            CaseRun(
                case=case,
                trace=trace,
                steps=len(trace),
                tokens=0,
                budget_hit=False,
            )
        )
    return tuple(runs)
