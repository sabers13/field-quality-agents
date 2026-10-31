"""The simulated engineer is deterministic and conservative."""

from __future__ import annotations

from datetime import UTC, datetime

from helpers import make_case

from field_quality_agents.agents.simulated_engineer import decide
from field_quality_agents.contracts import (
    Citation,
    DecisionAction,
    DecisionActor,
    Proposal,
    ProposalKind,
    SourceType,
    TargetedTest,
)

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


def proposal(kind: ProposalKind, *, verified: bool = True, evidence: bool = True) -> Proposal:
    citations = (
        (
            Citation(
                source_type=SourceType.CASE,
                source_id="CASE-1",
                quote="goes blank when the cabin is cold",
                verified=verified,
            ),
        )
        if evidence
        else ()
    )
    return Proposal(
        case_id="CASE-1",
        kind=kind,
        summary="A proposal",
        rationale="because the evidence says so",
        targeted_test=TargetedTest(name="Low-temperature cycling")
        if kind is ProposalKind.TARGETED_LOAD_TEST
        else None,
        evidence=citations,
        created_at=NOW,
    )


def state_for(item: Proposal | None) -> dict[str, object]:
    return {"case": make_case(), "proposal": item}


def test_approves_a_targeted_test_with_verified_quotes() -> None:
    decision = decide(state_for(proposal(ProposalKind.TARGETED_LOAD_TEST)), now=NOW)  # type: ignore[arg-type]
    assert decision.action is DecisionAction.APPROVE
    assert decision.actor is DecisionActor.SIMULATED_ENGINEER
    assert decision.proposal_kind is ProposalKind.TARGETED_LOAD_TEST
    assert decision.decided_at == NOW


def test_sends_back_a_targeted_test_without_evidence() -> None:
    decision = decide(
        state_for(proposal(ProposalKind.TARGETED_LOAD_TEST, evidence=False)),  # type: ignore[arg-type]
        now=NOW,
    )
    assert decision.action is DecisionAction.ASK
    assert "verified quote" in decision.rationale


def test_sends_back_unverified_evidence() -> None:
    decision = decide(
        state_for(proposal(ProposalKind.STANDARD_TEST, verified=False)),  # type: ignore[arg-type]
        now=NOW,
    )
    assert decision.action is DecisionAction.ASK
    assert "verification" in decision.rationale


def test_approves_an_information_request() -> None:
    decision = decide(
        state_for(proposal(ProposalKind.REQUEST_INFO, evidence=False)),  # type: ignore[arg-type]
        now=NOW,
    )
    assert decision.action is DecisionAction.APPROVE


def test_approves_safety_priority() -> None:
    decision = decide(
        state_for(proposal(ProposalKind.SAFETY_PRIORITY, evidence=False)),  # type: ignore[arg-type]
        now=NOW,
    )
    assert decision.action is DecisionAction.APPROVE


def test_asks_when_there_is_no_proposal() -> None:
    decision = decide(state_for(None), now=NOW)  # type: ignore[arg-type]
    assert decision.action is DecisionAction.ASK
    assert decision.proposal_kind is None
