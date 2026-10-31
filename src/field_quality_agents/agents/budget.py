"""Budget guard: a case over 12 steps or 40k tokens goes to a human."""

from __future__ import annotations

from field_quality_agents.agents.state import (
    DeskState,
    StepWriter,
    budget_reason,
)
from field_quality_agents.contracts import CaseStatus


def budget(state: DeskState) -> dict[str, object]:
    case = state["case"]
    writer = StepWriter(state)
    reason = budget_reason(state)
    writer.add(
        agent="budget",
        action="budget_exhausted",
        reason=reason,
        counts=False,
    )
    updated = case.model_copy(update={"status": CaseStatus.NEEDS_ENGINEER})
    return writer.updates(case=updated)
