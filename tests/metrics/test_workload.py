"""Hand-computed fixtures for the workload metrics over Q5 ``CaseRun`` records."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from field_quality_agents.agents.state import CaseRun
from field_quality_agents.contracts import (
    Case,
    DecisionAction,
    DecisionActor,
    HumanDecision,
    TraceStep,
)
from field_quality_agents.metrics import workload

START = datetime(2025, 1, 2, 9, 0, tzinfo=UTC)


def _case(case_id: str) -> Case:
    return Case(
        id=case_id,
        received_at=date(2025, 1, 2),
        make="HONDA",
        model="ACCORD",
        year=2020,
        component="EXTERIOR LIGHTING",
        narrative="The headlights fail intermittently.",
        group="lighting",
    )


def _step(index: int, agent: str, duration_ms: int, cost: float) -> TraceStep:
    return TraceStep(
        step=index,
        agent=agent,
        action="act",
        started_at=START,
        duration_ms=duration_ms,
        cost_usd=cost,
    )


def _decision(case_id: str, action: DecisionAction) -> HumanDecision:
    return HumanDecision(
        case_id=case_id,
        action=action,
        actor=DecisionActor.SIMULATED_ENGINEER,
        decided_at=START,
    )


def test_workload_matches_hand_computation() -> None:
    first = CaseRun(
        case=_case("C1"),
        trace=(
            _step(1, "human", 10, 0.0),
            _step(2, "analysis", 20, 0.01),
            _step(3, "human", 30, 0.0),
        ),
        decision=_decision("C1", DecisionAction.APPROVE),
        steps=3,
        budget_hit=False,
    )
    second = CaseRun(
        case=_case("C2"),
        trace=(
            _step(1, "human", 40, 0.02),
            _step(2, "analysis", 60, 0.03),
        ),
        decision=_decision("C2", DecisionAction.OVERRIDE),
        steps=5,
        budget_hit=True,
    )

    result = workload([first, second])

    assert result["human_touches_per_case"] == pytest.approx(1.5)  # 3 touches / 2 cases
    assert result["decided_without_edits_share"] == pytest.approx(0.5)  # 1 approve / 2
    assert result["steps_per_case"] == pytest.approx(4.0)  # (3 + 5) / 2
    assert result["cost_per_1000_cases_usd"] == pytest.approx(30.0)  # 0.06 / 2 * 1000
    assert result["latency_p50_ms"] == pytest.approx(80.0)  # 60 and 100
    assert result["latency_p95_ms"] == pytest.approx(98.0)
    assert result["budget_hits"] == 1.0


def test_empty_run_reports_zeros() -> None:
    result = workload([])
    assert all(value == 0.0 for value in result.values())


def test_pending_case_counts_as_a_touch_but_not_a_decision() -> None:
    pending = CaseRun(
        case=_case("C1"),
        trace=(_step(1, "human", 5, 0.0),),
        decision=None,
        steps=1,
        pending=True,
    )
    result = workload([pending])
    assert result["human_touches_per_case"] == 1.0
    assert result["decided_without_edits_share"] == 0.0
