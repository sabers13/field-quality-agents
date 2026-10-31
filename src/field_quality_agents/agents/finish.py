"""Finish node: settle the case status from the recorded human decision."""

from __future__ import annotations

from field_quality_agents.agents.gate import decidable
from field_quality_agents.agents.state import DeskState, StepWriter
from field_quality_agents.contracts import CaseStatus, DecisionAction


def finish(state: DeskState) -> dict[str, object]:
    case = state["case"]
    decision = state.get("decision")
    proposal = state.get("proposal")
    writer = StepWriter(state)

    approved = (
        decision is not None
        and decision.action in (DecisionAction.APPROVE, DecisionAction.OVERRIDE)
        and decidable(proposal)
    )
    if approved:
        status = CaseStatus.DECIDED
        action = "finish:decided"
        reason = "a human approved a concrete proposal"
    elif decision is not None:
        status = CaseStatus.NEEDS_ENGINEER
        action = "finish:needs_engineer"
        reason = f"human decision was {decision.action.value}; the case stays with an engineer"
    else:
        status = CaseStatus.NEEDS_ENGINEER
        action = "finish:needs_engineer"
        reason = "no human decision exists; the case cannot be decided"

    writer.add(agent="supervisor", action=action, reason=reason, counts=False)
    return writer.updates(case=case.model_copy(update={"status": status}))
