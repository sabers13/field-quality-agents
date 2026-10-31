"""Deterministic simulated engineer for batch runs.

PLAN §4: the simulated engineer approves when quotes verify and no hard rule is
broken, and sends the case back once otherwise. It never closes, scraps or
charges anything, and every decision says it is simulated.
"""

from __future__ import annotations

from datetime import datetime

from field_quality_agents.agents.state import DeskState, utcnow
from field_quality_agents.contracts import (
    DecisionAction,
    DecisionActor,
    HumanDecision,
    ProposalKind,
)


def _decision(
    state: DeskState,
    action: DecisionAction,
    rationale: str,
    now: datetime,
) -> HumanDecision:
    case = state["case"]
    proposal = state.get("proposal")
    return HumanDecision(
        case_id=case.id,
        action=action,
        actor=DecisionActor.SIMULATED_ENGINEER,
        rationale=rationale,
        decided_at=now,
        proposal_kind=proposal.kind if proposal is not None else None,
    )


def decide(state: DeskState, *, now: datetime | None = None) -> HumanDecision:
    """Return the simulated engineer's decision for the case in ``state``."""

    at = now or utcnow()
    proposal = state.get("proposal")
    if proposal is None:
        return _decision(
            state,
            DecisionAction.ASK,
            "No proposal to decide: the case goes to an engineer.",
            at,
        )

    if any(not citation.verified for citation in proposal.evidence):
        return _decision(
            state,
            DecisionAction.ASK,
            "Evidence failed quote verification: sending the case back.",
            at,
        )

    if proposal.kind is ProposalKind.TARGETED_LOAD_TEST and not proposal.evidence:
        return _decision(
            state,
            DecisionAction.ASK,
            "A targeted test needs at least one verified quote: sending the case back.",
            at,
        )

    if proposal.kind is ProposalKind.REQUEST_INFO:
        return _decision(
            state,
            DecisionAction.APPROVE,
            "The report is incomplete; the information request is ready.",
            at,
        )

    if proposal.kind is ProposalKind.SAFETY_PRIORITY:
        return _decision(
            state,
            DecisionAction.APPROVE,
            "Safety flag stands; the case keeps priority for a live engineer.",
            at,
        )

    return _decision(
        state,
        DecisionAction.APPROVE,
        "Quotes verified and no hard rule is broken.",
        at,
    )
