"""Hard rules live in code, not prompts: safety, evidence and no close action."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from helpers import (
    analysis_payload,
    intake_payload,
    make_case,
    run_desk,
)

from field_quality_agents.agents.state import MAX_STEPS, MAX_TOKENS
from field_quality_agents.contracts import (
    CaseStatus,
    DecisionAction,
    DecisionActor,
    HumanDecision,
    ProposalKind,
)

FORBIDDEN_ACTIONS = ("close", "scrap", "charge", "write off")


def test_no_closing_scrapping_or_charging_action_exists() -> None:
    assert {action.value for action in DecisionAction} == {
        "approve",
        "override",
        "ask",
        "request_info",
    }
    assert {kind.value for kind in ProposalKind} == {
        "standard_test",
        "targeted_load_test",
        "safety_priority",
        "evidence_pack",
        "request_info",
    }
    assert {status.value for status in CaseStatus} == {
        "new",
        "intake",
        "analysis",
        "needs_engineer",
        "decided",
        "issue_linked",
    }


def test_no_trace_action_names_a_closing_scrapping_or_charging_step() -> None:
    run, _model, _tools = run_desk(
        make_case(),
        intake=intake_payload(),
        analysis=analysis_payload(),
    )
    for step in run.trace:
        lowered = f"{step.action} {step.reason}".lower()
        for word in FORBIDDEN_ACTIONS:
            assert word not in lowered


def test_budgets_are_the_plan_values() -> None:
    assert MAX_STEPS == 12
    assert MAX_TOKENS == 40_000


def test_a_safety_case_reaches_a_human_before_any_analysis_step() -> None:
    run, _model, _tools = run_desk(
        make_case(safety_relevant=True),
        intake=intake_payload(safety=True),
    )
    assert not any(step.agent == "analysis" for step in run.trace)
    human = next(step for step in run.trace if step.agent == "human")
    safety = next(step for step in run.trace if step.agent == "safety")
    assert safety.step < human.step
    assert run.proposal is not None
    assert run.proposal.kind is ProposalKind.SAFETY_PRIORITY


def test_an_approved_information_request_never_decides_a_case() -> None:
    run, _model, _tools = run_desk(
        make_case(),
        intake=intake_payload(missing=("symptom",)),
    )
    assert run.decision is not None
    assert run.decision.action is DecisionAction.APPROVE
    assert run.case.status is CaseStatus.NEEDS_ENGINEER


def test_gate_rejects_a_decision_for_another_case() -> None:
    def wrong_case_engineer(state: object) -> HumanDecision:
        return HumanDecision(
            case_id="SOME-OTHER-CASE",
            action=DecisionAction.APPROVE,
            actor=DecisionActor.LIVE_ENGINEER,
            decided_at=datetime(2026, 10, 31, 12, 0, tzinfo=UTC),
        )

    with pytest.raises(ValueError, match="different case"):
        run_desk(
            make_case(),
            intake=intake_payload(),
            analysis=analysis_payload(),
            engineer=wrong_case_engineer,
        )


def test_unverified_quotes_are_never_evidence() -> None:
    run, _model, _tools = run_desk(
        make_case(),
        intake=intake_payload(),
        analysis=analysis_payload(
            quotes=("goes blank when the cabin is cold", "invented evidence")
        ),
    )
    assert run.proposal is not None
    assert run.proposal.evidence
    assert all(citation.verified for citation in run.proposal.evidence)
    assert all(
        citation.quote != "invented evidence" for citation in run.proposal.evidence
    )


def test_intake_drops_an_invented_quote_before_persisting_it() -> None:
    """A safety case never reaches analysis, so intake must verify its clues."""

    run, _model, _tools = run_desk(
        make_case(safety_relevant=True),
        intake=intake_payload(
            safety=True,
            quotes=("goes blank when the cabin is cold", "invented intake clue"),
        ),
    )
    assert run.extraction is not None
    kept = [clue.quote for clue in run.extraction.clues]
    assert kept == ["goes blank when the cabin is cold"]
    assert any(
        step.agent == "intake" and step.tool == "verify_quotes" for step in run.trace
    )
    assert any(step.action == "drop_unverified_quotes" for step in run.trace)


def test_the_model_never_sees_the_evaluation_labels() -> None:
    """PLAN §7 scores group and safety; both must stay out of the request."""

    run, model, _tools = run_desk(
        make_case(),
        intake=intake_payload(),
        analysis=analysis_payload(),
    )
    assert run.proposal is not None

    intake_call = next(call for call in model.calls if call["agent"] == "intake")
    intake_message = intake_call["messages"][1]
    assert isinstance(intake_message, dict)
    intake_payload_json = json.loads(str(intake_message["content"]))
    assert "group" not in intake_payload_json
    assert "safety_relevant" not in intake_payload_json

    analysis_call = next(call for call in model.calls if call["agent"] == "analysis")
    analysis_message = analysis_call["messages"][1]
    assert isinstance(analysis_message, dict)
    analysis_payload_json = json.loads(str(analysis_message["content"]))
    assert "group" not in analysis_payload_json["case"]
    assert "safety_relevant" not in analysis_payload_json["case"]


def test_the_truth_safety_flag_is_not_copied_into_the_prediction() -> None:
    """Scoring 'truth OR model' would report recall that the desk never earned."""

    run, _model, _tools = run_desk(
        make_case(safety_relevant=True),
        intake=intake_payload(safety=False, missing=("symptom",)),
    )
    assert run.extraction is not None
    assert run.extraction.safety_relevant is False
    assert run.case.safety_relevant is False
