"""Safety gate: a safety-relevant case gets a proposal before any test."""

from __future__ import annotations

from field_quality_agents.agents.state import DeskState, StepWriter, utcnow
from field_quality_agents.contracts import (
    CaseStatus,
    Proposal,
    ProposalKind,
)


def safety(state: DeskState) -> dict[str, object]:
    """Build the safety-priority proposal. Code, not the model, sets the kind."""

    case = state["case"]
    writer = StepWriter(state)
    writer.add(
        agent="safety",
        action="draft_safety_proposal",
        reason=(
            "case is flagged safety-relevant; a human sees it before any test decision is taken"
        ),
    )
    proposal = Proposal(
        case_id=case.id,
        kind=ProposalKind.SAFETY_PRIORITY,
        summary="Safety-relevant report: send to an engineer before further testing",
        rationale="The safety flag routes this case to a human first (PLAN §4).",
        created_at=utcnow(),
    )
    updated = case.model_copy(update={"status": CaseStatus.NEEDS_ENGINEER})
    return writer.updates(case=updated, proposal=proposal, safety_relevant=True)
