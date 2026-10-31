"""Supervisor routing.

The routing policy is code for the cases where PLAN §4 fixes it: safety goes to
a human first, an unfinished intake goes to intake, an analysed case without a
proposal goes to analysis, a proposal goes to a human, and a budget or a
recorded decision ends the routing. The supervisor still records every routing
choice as a ``TraceStep`` with its reason.
"""

from __future__ import annotations

from field_quality_agents.agents.state import (
    PROMPT_VERSION,
    DeskState,
    StepWriter,
    budget_exhausted,
)

ROUTE_REASONS: dict[str, str] = {
    "intake": "no extraction yet: normalise the report first",
    "safety": "safety-relevant case: build the safety proposal before any test",
    "analysis": "case normalised and no proposal yet: gather evidence",
    "human_gate": "a proposal needs a human decision",
    "budget": "case budget exhausted: hand to a human",
    "finish": "work complete for this case",
}


def route(state: DeskState) -> str:
    """Return the next graph node for ``state``."""

    if state.get("decision") is not None:
        return "finish"
    if budget_exhausted(state):
        return "budget"
    case = state.get("case")
    if case is None:
        return "finish"
    if state.get("extraction") is None:
        return "intake"
    if state.get("proposal") is None:
        return "safety" if state.get("safety_relevant") else "analysis"
    return "human_gate"


def supervisor(state: DeskState) -> dict[str, object]:
    writer = StepWriter(state)
    target = route(state)
    writer.add(
        agent="supervisor",
        action=f"route:{target}",
        reason=f"{ROUTE_REASONS[target]} (prompt {PROMPT_VERSION})",
        counts=False,
    )
    return writer.updates()
