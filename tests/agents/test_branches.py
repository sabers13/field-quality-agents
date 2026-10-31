"""Every branch of the desk graph, driven by a scripted fake model."""

from __future__ import annotations

from datetime import UTC, datetime

from helpers import (
    analysis_payload,
    intake_payload,
    make_case,
    run_desk,
)

from field_quality_agents.agents.state import MAX_STEPS, CaseRun, DeskState
from field_quality_agents.contracts import (
    CaseStatus,
    DecisionAction,
    DecisionActor,
    HumanDecision,
    ProposalKind,
)


def actions(run: CaseRun) -> list[str]:
    return [step.action for step in run.trace]


def test_targeted_test_branch_uses_tools_and_verified_quotes() -> None:
    run, model, tools = run_desk(
        make_case(),
        intake=intake_payload(),
        analysis=analysis_payload(),
    )

    assert run.case.status is CaseStatus.DECIDED
    assert run.proposal is not None
    assert run.proposal.kind is ProposalKind.TARGETED_LOAD_TEST
    assert run.proposal.targeted_test is not None
    assert run.proposal.targeted_test.name == "Low-temperature cycling"
    assert run.proposal.evidence
    assert all(citation.verified for citation in run.proposal.evidence)
    assert run.decision is not None
    assert run.decision.action is DecisionAction.APPROVE
    assert run.decision.actor is DecisionActor.SIMULATED_ENGINEER
    assert run.budget_hit is False
    assert run.pending is False
    assert run.steps <= MAX_STEPS
    assert run.prompt_version == "p1"

    assert "search_similar_cases" in actions(run)
    assert "lookup_recalls" in actions(run)
    assert "lookup_investigations" in actions(run)
    assert "read_rulebook" in actions(run)
    assert "verify_quotes" in actions(run)
    called = [name for name, _payload in tools.calls]
    assert called.count("similar_cases") == 2  # intake duplicate check + analysis
    assert model.calls[0]["agent"] == "intake"
    assert model.calls[1]["agent"] == "analysis"


def test_safety_branch_reaches_a_human_before_analysis() -> None:
    case = make_case(
        safety_relevant=True,
        narrative="Smoke came from the display and the car lost power at speed.",
    )
    run, _model, tools = run_desk(
        case,
        intake=intake_payload(safety=True, quotes=("Smoke came from the display",)),
    )

    assert run.proposal is not None
    assert run.proposal.kind is ProposalKind.SAFETY_PRIORITY
    assert run.decision is not None
    assert run.decision.action is DecisionAction.APPROVE
    assert run.case.status is CaseStatus.DECIDED

    assert "search_similar_cases" not in actions(run)
    assert ("rulebook" not in [name for name, _payload in tools.calls])
    human_at = actions(run).index("decision:approve")
    assert human_at < len(actions(run))
    assert not any(step.agent == "analysis" for step in run.trace)


def test_missing_information_branch_requests_a_report() -> None:
    run, _model, _tools = run_desk(
        make_case(),
        intake=intake_payload(missing=("mileage", "conditions")),
    )

    assert run.proposal is not None
    assert run.proposal.kind is ProposalKind.REQUEST_INFO
    assert run.proposal.requested_info == ("mileage", "conditions")
    assert "draft_info_request" in actions(run)
    assert run.decision is not None
    assert run.decision.action is DecisionAction.APPROVE
    # An approved information request never decides the case.
    assert run.case.status is CaseStatus.NEEDS_ENGINEER
    assert "search_similar_cases" not in actions(run)


def test_budget_hit_hands_the_case_to_a_human() -> None:
    run, _model, _tools = run_desk(
        make_case(),
        intake=intake_payload(tokens=40_000),
    )

    assert run.budget_hit is True
    assert run.case.status is CaseStatus.NEEDS_ENGINEER
    assert run.proposal is None
    assert run.decision is not None
    assert run.decision.action is DecisionAction.ASK
    assert "budget_exhausted" in actions(run)
    assert run.steps < MAX_STEPS


def test_human_override_uses_the_edited_proposal() -> None:
    def overriding_engineer(state: DeskState) -> HumanDecision:
        proposal = state["proposal"]
        edited = proposal.model_copy(
            update={"summary": "Engineer edit: visual inspection before cycling"}
        )
        return HumanDecision(
            case_id=proposal.case_id,
            action=DecisionAction.OVERRIDE,
            actor=DecisionActor.LIVE_ENGINEER,
            rationale="Check the connector first.",
            decided_at=datetime(2026, 10, 31, 12, 0, tzinfo=UTC),
            edited_proposal=edited,
        )

    run, _model, _tools = run_desk(
        make_case(),
        intake=intake_payload(),
        analysis=analysis_payload(),
        engineer=overriding_engineer,
    )

    assert run.decision is not None
    assert run.decision.action is DecisionAction.OVERRIDE
    assert run.decision.actor is DecisionActor.LIVE_ENGINEER
    assert run.proposal is not None
    assert run.proposal.summary == "Engineer edit: visual inspection before cycling"
    assert run.case.status is CaseStatus.DECIDED
    assert "decision:override" in actions(run)


def test_ask_keeps_the_case_with_an_engineer() -> None:
    def asking_engineer(state: DeskState) -> HumanDecision:
        case = state["case"]
        return HumanDecision(
            case_id=case.id,
            action=DecisionAction.ASK,
            actor=DecisionActor.LIVE_ENGINEER,
            rationale="Ask the lab to confirm the setup.",
            decided_at=datetime(2026, 10, 31, 12, 0, tzinfo=UTC),
        )

    run, _model, _tools = run_desk(
        make_case(),
        intake=intake_payload(),
        analysis=analysis_payload(),
        engineer=asking_engineer,
    )

    assert run.decision is not None
    assert run.decision.action is DecisionAction.ASK
    assert run.case.status is CaseStatus.NEEDS_ENGINEER
    assert "decision:ask" in actions(run)


def test_unreadable_intake_answer_is_not_a_decision() -> None:
    from field_quality_agents.agents.model import ModelTurn

    run, _model, _tools = run_desk(
        make_case(),
        intake=ModelTurn(text="I could not read the report, sorry."),
    )

    assert run.proposal is not None
    assert run.proposal.kind is ProposalKind.REQUEST_INFO
    assert run.case.status is CaseStatus.NEEDS_ENGINEER
    assert "unreadable_model_output" in actions(run)


def test_failing_quotes_are_dropped_from_evidence() -> None:
    run, _model, _tools = run_desk(
        make_case(),
        intake=intake_payload(),
        analysis=analysis_payload(
            quotes=(
                "goes blank when the cabin is cold",
                "this sentence is not in the report",
            )
        ),
    )

    assert run.extraction is not None
    assert len(run.extraction.clues) == 1
    assert run.proposal is not None
    assert len(run.proposal.evidence) == 1
    assert run.proposal.evidence[0].quote == "goes blank when the cabin is cold"
    assert "drop_unverified_quotes" in actions(run)


def test_safety_found_late_by_analysis_still_reaches_a_human() -> None:
    run, _model, _tools = run_desk(
        make_case(),
        intake=intake_payload(),
        analysis=analysis_payload(safety=True),
    )

    assert run.proposal is not None
    assert run.proposal.kind is ProposalKind.SAFETY_PRIORITY
    assert run.case.safety_relevant is True
    assert "decision:approve" in actions(run)
    assert run.case.status is CaseStatus.DECIDED
