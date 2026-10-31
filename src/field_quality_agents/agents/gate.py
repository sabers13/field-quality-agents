"""Human checkpoint.

The graph suspends here with ``interrupt``. A live dashboard resumes it with
``Command(resume=HumanDecision)``; batch runs use the deterministic simulated
engineer. Code enforces the hard rule: a case reaches ``decided`` only through
an approve or override that names a concrete proposal.
"""

from __future__ import annotations

from collections.abc import Mapping

from langgraph.types import interrupt

from field_quality_agents.agents.state import DeskState, StepWriter
from field_quality_agents.contracts import (
    CaseStatus,
    DecisionAction,
    HumanDecision,
    Proposal,
    ProposalKind,
)


def _gate_reason(state: DeskState) -> str:
    if state.get("proposal") is None:
        return "the case has no proposal: hand to an engineer"
    if state.get("safety_relevant"):
        return "safety-relevant case: a human decides before any test"
    return "a test decision needs a human"


def _coerce_decision(response: object, case_id: str) -> HumanDecision:
    if isinstance(response, HumanDecision):
        decision = response
    elif isinstance(response, Mapping):
        decision = HumanDecision.model_validate(dict(response))
    else:
        raise TypeError("a human checkpoint needs a HumanDecision to resume")
    if decision.case_id != case_id:
        raise ValueError("the human decision names a different case")
    return decision


def decidable(proposal: Proposal | None) -> bool:
    """Only a test or safety proposal can decide a case; an info request cannot."""

    return proposal is not None and proposal.kind in (
        ProposalKind.STANDARD_TEST,
        ProposalKind.TARGETED_LOAD_TEST,
        ProposalKind.SAFETY_PRIORITY,
    )


def _resolve(
    decision: HumanDecision,
    proposal: Proposal | None,
    case_id: str,
) -> tuple[Proposal | None, CaseStatus]:
    if decision.action is DecisionAction.OVERRIDE and decision.edited_proposal is not None:
        if decision.edited_proposal.case_id != case_id:
            raise ValueError("the edited proposal names a different case")
        proposal = decision.edited_proposal
    approved = decision.action in (
        DecisionAction.APPROVE,
        DecisionAction.OVERRIDE,
    )
    if approved and decidable(proposal):
        return proposal, CaseStatus.DECIDED
    return proposal, CaseStatus.NEEDS_ENGINEER


def human_gate(state: DeskState) -> dict[str, object]:
    case = state["case"]
    proposal = state.get("proposal")
    payload = {
        "case_id": case.id,
        "reason": _gate_reason(state),
        "proposal": proposal.model_dump(mode="json") if proposal is not None else None,
    }
    response = interrupt(payload)
    decision = _coerce_decision(response, case.id)

    resolved, status = _resolve(decision, proposal, case.id)
    if decision.proposal_kind is None and resolved is not None:
        decision = decision.model_copy(update={"proposal_kind": resolved.kind})

    writer = StepWriter(state)
    writer.add(
        agent="human",
        action=f"decision:{decision.action.value}",
        reason=decision.rationale or _gate_reason(state),
        counts=False,
    )
    updated = case.model_copy(update={"status": status})
    return writer.updates(
        case=updated,
        proposal=resolved,
        decision=decision,
        pending_decision=None,
    )
