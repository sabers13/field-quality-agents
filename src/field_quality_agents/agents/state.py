"""State, budgets and result shapes for the agentic desk.

The ``DeskState`` keys mirror ``docs/INTERFACES.md`` §Q5. ``trace`` is the one
addition: an ``operator.add`` reducer so a node appends its steps and the graph
keeps the whole history in checkpoint order.
"""

from __future__ import annotations

import operator
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated, TypedDict

from field_quality_agents.contracts import (
    Case,
    CaseStatus,
    Extraction,
    HumanDecision,
    Proposal,
    TraceStep,
)

#: PLAN §4 budgets: a case that reaches either limit goes to a human.
MAX_STEPS = 12
MAX_TOKENS = 40_000

#: Prompts are versioned files under ``prompts/<agent>/<version>.md``.
PROMPT_VERSION = "p1"

#: Upper bound on human checkpoints in one batch run, guarding a resume loop.
MAX_CHECKPOINTS = 4


class DeskState(TypedDict, total=False):
    """One case moving through the desk graph."""

    case: Case
    extraction: Extraction
    proposal: Proposal
    trace: Annotated[list[TraceStep], operator.add]
    steps: int
    tokens: int
    safety_relevant: bool
    pending_decision: HumanDecision | None
    decision: HumanDecision | None
    issue_ids: list[str]


@dataclass(frozen=True)
class CaseRun:
    """The outcome of one case: state, trace and the human decision."""

    case: Case
    trace: tuple[TraceStep, ...]
    extraction: Extraction | None = None
    proposal: Proposal | None = None
    decision: HumanDecision | None = None
    steps: int = 0
    tokens: int = 0
    budget_hit: bool = False
    pending: bool = False
    prompt_version: str = PROMPT_VERSION

    @property
    def decided(self) -> bool:
        """True only when a human approved or overrode a concrete proposal."""

        return self.decision is not None and self.case.status is CaseStatus.DECIDED


@dataclass
class StepWriter:
    """Append ``TraceStep`` objects and account for them as budget steps."""

    state: DeskState
    _written: list[TraceStep] = field(default_factory=list)
    _counted: int = 0

    def add(
        self,
        *,
        agent: str,
        action: str,
        reason: str = "",
        tool: str | None = None,
        tool_input: dict[str, object] | None = None,
        tool_output: dict[str, object] | None = None,
        tokens: int = 0,
        cost_usd: float = 0.0,
        duration_ms: int = 0,
        counts: bool = True,
    ) -> TraceStep:
        number = len(self.state.get("trace", [])) + len(self._written) + 1
        step = TraceStep(
            step=number,
            agent=agent,
            action=action,
            reason=reason,
            tool=tool,
            tool_input=tool_input,
            tool_output=tool_output,
            started_at=utcnow(),
            duration_ms=duration_ms,
            tokens=tokens,
            cost_usd=cost_usd,
        )
        self._written.append(step)
        if counts:
            self._counted += 1
        return step

    def updates(self, **extra: object) -> dict[str, object]:
        update: dict[str, object] = {
            "trace": list(self._written),
            "steps": self.state.get("steps", 0) + self._counted,
        }
        update.update(extra)
        return update


def utcnow() -> datetime:
    return datetime.now(UTC)


Node = Callable[[DeskState], dict[str, object]]


def budget_exhausted(state: DeskState) -> bool:
    return state.get("steps", 0) >= MAX_STEPS or state.get("tokens", 0) >= MAX_TOKENS


def budget_reason(state: DeskState) -> str:
    """Return the budget that tripped first, in words for the trace."""

    steps = state.get("steps", 0)
    tokens = state.get("tokens", 0)
    if steps >= MAX_STEPS and tokens >= MAX_TOKENS:
        return f"budget hit: {steps} steps and {tokens} tokens"
    if steps >= MAX_STEPS:
        return f"budget hit: {steps} of {MAX_STEPS} steps used"
    return f"budget hit: {tokens} of {MAX_TOKENS} tokens used"
