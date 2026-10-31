"""Trace, token accounting and the day seam."""

from __future__ import annotations

from datetime import date

from helpers import (
    analysis_payload,
    build_graph,
    intake_payload,
    make_case,
    run_desk,
)

from field_quality_agents.agents import initial_state, run_day


def test_every_step_is_appended_and_tokens_are_summed() -> None:
    run, model, _tools = run_desk(
        make_case(),
        intake=intake_payload(tokens=120),
        analysis=analysis_payload(),
    )

    assert run.tokens == 360
    assert sum(step.tokens for step in run.trace) == 360
    assert [step.step for step in run.trace] == list(range(1, len(run.trace) + 1))
    assert [call["agent"] for call in model.calls] == ["intake", "analysis"]
    assert 6 <= run.steps <= 12


def test_initial_state_is_empty_except_for_the_case() -> None:
    case = make_case()
    state = initial_state(case)
    assert state["case"] == case
    assert state["trace"] == []
    assert state["steps"] == 0
    assert state["tokens"] == 0


def test_run_day_stops_at_the_day_boundary() -> None:
    first = make_case(id="CASE-EARLY", received_at=date(2025, 3, 4))
    second = make_case(id="CASE-LATE", received_at=date(2025, 3, 10))
    graph, _model, _tools = build_graph(
        intake=intake_payload(missing=("mileage",)),
    )

    issues = run_day([first, second], date(2025, 3, 5), graph)

    assert issues == []
