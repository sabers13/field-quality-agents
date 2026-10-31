"""Property test: no path decides a case without a human decision.

The graph is driven through its whole branch matrix, then through a seeded
random matrix of reports, proposals and engineer actions. Two invariants hold
every time:

* ``decided`` implies a human approve or override naming a decidable proposal;
* every trace is contiguous and every case finishes inside its step budget.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from helpers import (
    analysis_payload,
    intake_payload,
    make_case,
    run_desk,
)

from field_quality_agents.agents.gate import decidable
from field_quality_agents.agents.model import ModelTurn
from field_quality_agents.agents.state import MAX_STEPS, CaseRun, DeskState
from field_quality_agents.contracts import (
    CaseStatus,
    DecisionAction,
    DecisionActor,
    HumanDecision,
)

AT = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
AGENTS = {"supervisor", "intake", "safety", "analysis", "budget", "human"}


def decide_manually(action: DecisionAction) -> Callable[[DeskState], HumanDecision]:
    def engineer(state: DeskState) -> HumanDecision:
        proposal = state.get("proposal")
        edited = (
            proposal.model_copy(update={"summary": "Engineer edit"})
            if action is DecisionAction.OVERRIDE and proposal is not None
            else None
        )
        return HumanDecision(
            case_id=state["case"].id,
            action=action,
            actor=DecisionActor.LIVE_ENGINEER,
            rationale="property-test decision",
            decided_at=AT,
            edited_proposal=edited,
        )

    return engineer


def check_invariants(run: CaseRun) -> None:
    assert run.pending is False
    assert run.case.status in (CaseStatus.DECIDED, CaseStatus.NEEDS_ENGINEER)
    assert run.steps <= MAX_STEPS
    assert [step.step for step in run.trace] == list(range(1, len(run.trace) + 1))
    assert {step.agent for step in run.trace} <= AGENTS

    if run.case.status is CaseStatus.DECIDED:
        assert run.decision is not None, "a decided case must carry a HumanDecision"
        assert run.decision.action in (
            DecisionAction.APPROVE,
            DecisionAction.OVERRIDE,
        )
        assert decidable(run.proposal)


def run_case_scenario(name: str) -> CaseRun:
    if name == "targeted":
        run, _model, _tools = run_desk(
            make_case(),
            intake=intake_payload(),
            analysis=analysis_payload(),
        )
        return run
    if name == "safety":
        run, _model, _tools = run_desk(
            make_case(safety_relevant=True),
            intake=intake_payload(safety=True),
        )
        return run
    if name == "missing_info":
        run, _model, _tools = run_desk(
            make_case(), intake=intake_payload(missing=("mileage",))
        )
        return run
    if name == "budget":
        run, _model, _tools = run_desk(make_case(), intake=intake_payload(tokens=40_000))
        return run
    if name == "override":
        run, _model, _tools = run_desk(
            make_case(),
            intake=intake_payload(),
            analysis=analysis_payload(),
            engineer=decide_manually(DecisionAction.OVERRIDE),
        )
        return run
    if name == "ask":
        run, _model, _tools = run_desk(
            make_case(),
            intake=intake_payload(),
            analysis=analysis_payload(),
            engineer=decide_manually(DecisionAction.ASK),
        )
        return run
    if name == "request_info":
        run, _model, _tools = run_desk(
            make_case(),
            intake=intake_payload(missing=("mileage",)),
            engineer=decide_manually(DecisionAction.REQUEST_INFO),
        )
        return run
    if name == "unreadable":
        run, _model, _tools = run_desk(
            make_case(), intake=ModelTurn(text="no json here")
        )
        return run
    raise AssertionError(f"unknown scenario {name}")


@pytest.mark.parametrize(
    "name",
    [
        "targeted",
        "safety",
        "missing_info",
        "budget",
        "override",
        "ask",
        "request_info",
        "unreadable",
    ],
)
def test_no_branch_decides_without_a_human_decision(name: str) -> None:
    check_invariants(run_case_scenario(name))


def test_random_matrix_never_decides_without_a_human_decision() -> None:
    rng = random.Random(20261031)
    actions = list(DecisionAction)
    for index in range(40):
        safety = rng.random() < 0.3
        missing = rng.random() < 0.2
        targeted = rng.random() < 0.7
        good_quote = rng.random() < 0.8

        case = make_case(
            id=f"CASE-{index}",
            safety_relevant=safety,
            narrative="The display goes blank when the cabin is cold.",
        )
        intake = intake_payload(
            safety=safety,
            missing=("mileage",) if missing else (),
            quotes=("goes blank when the cabin is cold",),
        )
        analysis = None
        if not safety and not missing:
            analysis = analysis_payload(
                targeted=targeted,
                quotes=(
                    ("goes blank when the cabin is cold",)
                    if good_quote
                    else ("this quote is not in the report",)
                ),
            )
        action = rng.choice(actions)
        run, _model, _tools = run_desk(
            case,
            intake=intake,
            analysis=analysis,
            engineer=decide_manually(action),
        )
        check_invariants(run)
