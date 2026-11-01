"""Live-mode decisions: resume the desk graph from its checkpoint.

The batch run never uses this module. In live mode the dashboard's approve,
override and ask buttons arrive here, and the graph is resumed with a
``HumanDecision`` carrying ``actor="live_engineer"``.

``ask`` and ``request_info`` deliberately do not resume the graph: they append
a visible human step, leave the case at ``needs_engineer`` and keep the
checkpoint interrupt so a later approve or override is still possible.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any, Protocol, cast

from langgraph.types import Command

from field_quality_agents.agents.graph import initial_state
from field_quality_agents.agents.state import utcnow
from field_quality_agents.api.store import CaseRecord
from field_quality_agents.contracts import (
    Case,
    CaseStatus,
    DecisionAction,
    DecisionActor,
    Extraction,
    HumanDecision,
    Proposal,
    TraceStep,
)

__all__ = [
    "GraphLike",
    "InvalidDecisionError",
    "LiveDesk",
    "LiveError",
    "NotAwaitingError",
    "UnknownCaseError",
]

_CHECKPOINT_ACTIONS = (DecisionAction.APPROVE, DecisionAction.OVERRIDE)


class LiveError(RuntimeError):
    """Base class for a live decision that cannot proceed."""


class UnknownCaseError(LiveError):
    """No live thread is registered for this case."""


class NotAwaitingError(LiveError):
    """The case is not sitting at a human checkpoint."""


class InvalidDecisionError(LiveError):
    """The request contradicts the case or the checkpoint."""


class GraphLike(Protocol):
    """The part of ``CompiledStateGraph`` the live desk calls.

    ``langgraph``'s compiled graph satisfies this structurally; tests pass a
    small fake with the same two methods. ``Any`` keeps the protocol usable for
    both LangGraph's generic signatures and the fake.
    """

    def invoke(self, input: Any, config: Any = None) -> Any: ...

    def get_state(self, config: Any) -> Any: ...


def _values(snapshot: object) -> dict[str, object]:
    values = getattr(snapshot, "values", None)
    if isinstance(values, Mapping):
        return dict(cast(Mapping[str, object], values))
    return {}


def _interrupted(snapshot: object) -> bool:
    return bool(getattr(snapshot, "interrupts", ()))


def _trace(values: Mapping[str, object]) -> tuple[TraceStep, ...]:
    raw = values.get("trace", ())
    if not isinstance(raw, (list, tuple)):
        return ()
    return tuple(step for step in raw if isinstance(step, TraceStep))


def _transition_index(trace: list[TraceStep]) -> int:
    """Index of the first resumed human decision, or the end of the trace."""

    for index, step in enumerate(trace):
        if step.agent == "human" and step.action.startswith("decision:"):
            return index
    return len(trace)


def _merge(
    trace: tuple[TraceStep, ...],
    overlay: tuple[TraceStep, ...],
) -> tuple[TraceStep, ...]:
    """Put overlay-only human steps before the graph's resumed decision step."""

    if not overlay:
        return trace
    index = _transition_index(list(trace))
    merged = list(trace[:index]) + list(overlay) + list(trace[index:])
    return tuple(step.model_copy(update={"step": number}) for number, step in enumerate(merged, 1))


def _record(
    values: Mapping[str, object],
    fallback: Case,
    overlay: tuple[TraceStep, ...] = (),
) -> CaseRecord:
    case = values.get("case")
    extraction = values.get("extraction")
    proposal = values.get("proposal")
    decision = values.get("decision")
    return CaseRecord(
        case=case if isinstance(case, Case) else fallback,
        trace=_merge(_trace(values), overlay),
        extraction=extraction if isinstance(extraction, Extraction) else None,
        proposal=proposal if isinstance(proposal, Proposal) else None,
        decision=decision if isinstance(decision, HumanDecision) else None,
    )


class LiveDesk:
    """Track live graph threads and turn dashboard actions into decisions."""

    def __init__(
        self,
        graph: GraphLike,
        *,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._graph = graph
        self._clock = clock
        self._threads: dict[str, dict[str, object]] = {}
        self._records: dict[str, CaseRecord] = {}
        self._awaiting: set[str] = set()
        self._overlay: dict[str, list[TraceStep]] = {}

    def start(self, case: Case, *, thread_id: str | None = None) -> CaseRecord:
        """Run a case until its first checkpoint and register the thread."""

        config: dict[str, object] = {
            "configurable": {"thread_id": thread_id or f"{case.id}-live"}
        }
        self._graph.invoke(initial_state(case), config)
        self._threads[case.id] = config
        return self._refresh(case.id, fallback=case)

    def track(self, case: Case) -> None:
        """Show a case the live run already started elsewhere."""

        self._records.setdefault(case.id, CaseRecord(case=case))

    def record(self, case_id: str) -> CaseRecord | None:
        return self._records.get(case_id)

    def records(self) -> tuple[CaseRecord, ...]:
        return tuple(self._records.values())

    def awaiting(self, case_id: str) -> bool:
        return case_id in self._awaiting

    def decide(
        self,
        case_id: str,
        *,
        action: DecisionAction,
        rationale: str,
        edited_proposal: Proposal | None = None,
    ) -> CaseRecord:
        config = self._threads.get(case_id)
        if config is None:
            if case_id in self._records:
                raise NotAwaitingError(f"{case_id} is not sitting at a human checkpoint")
            raise UnknownCaseError(f"no live thread for {case_id}")

        snapshot = self._graph.get_state(config)
        if not _interrupted(snapshot):
            raise NotAwaitingError(f"{case_id} is not sitting at a human checkpoint")

        values = _values(snapshot)
        known = self._records.get(case_id)
        fallback = known.case if known is not None else cast(Case, values.get("case"))
        proposal = values.get("proposal")
        decision = HumanDecision(
            case_id=case_id,
            action=action,
            actor=DecisionActor.LIVE_ENGINEER,
            rationale=rationale,
            decided_at=self._clock(),
            proposal_kind=proposal.kind if isinstance(proposal, Proposal) else None,
            edited_proposal=edited_proposal,
        )

        if action in _CHECKPOINT_ACTIONS:
            if (
                edited_proposal is not None
                and edited_proposal.case_id != case_id
            ):
                raise InvalidDecisionError("the edited proposal names a different case")
            self._graph.invoke(Command[HumanDecision](resume=decision), config)
            return self._refresh(case_id, fallback=fallback)

        return self._append_human_step(
            case_id,
            values,
            fallback,
            action=action,
            rationale=rationale,
        )

    def _refresh(self, case_id: str, *, fallback: Case) -> CaseRecord:
        config = self._threads[case_id]
        snapshot = self._graph.get_state(config)
        overlay = tuple(self._overlay.get(case_id, ()))
        record = _record(_values(snapshot), fallback, overlay)
        self._records[case_id] = record
        if _interrupted(snapshot):
            self._awaiting.add(case_id)
        else:
            self._awaiting.discard(case_id)
        return record

    def _append_human_step(
        self,
        case_id: str,
        values: Mapping[str, object],
        fallback: Case,
        *,
        action: DecisionAction,
        rationale: str,
    ) -> CaseRecord:
        trace = list(_trace(values))
        step = TraceStep(
            step=len(trace) + 1,
            agent="live_engineer",
            action=f"decision:{action.value}",
            reason=rationale or "a live engineer recorded this action",
            started_at=self._clock(),
        )
        overlay = self._overlay.setdefault(case_id, [])
        overlay.append(step)
        base = _record(values, fallback, tuple(self._overlay[case_id]))
        updated = base.case.model_copy(update={"status": CaseStatus.NEEDS_ENGINEER})
        record = CaseRecord(
            case=updated,
            trace=base.trace,
            extraction=base.extraction,
            proposal=base.proposal,
            decision=base.decision,
        )
        self._records[case_id] = record
        self._awaiting.add(case_id)
        return record
