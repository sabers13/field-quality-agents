"""Case board and case detail endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from field_quality_agents.api.deps import (
    bus_of,
    case_records,
    desk_of,
    find_case,
    mode_of,
    store_of,
)
from field_quality_agents.api.live import (
    InvalidDecisionError,
    NotAwaitingError,
    UnknownCaseError,
)
from field_quality_agents.api.models import (
    CaseDetail,
    CaseListItem,
    CaseListPage,
    DecisionRequest,
    DecisionResponse,
    TraceResponse,
)
from field_quality_agents.api.store import CaseRecord
from field_quality_agents.contracts import CaseStatus

__all__ = ["router"]

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _human_touches(record: CaseRecord) -> int:
    steps = sum(1 for step in record.trace if step.agent in ("human", "live_engineer"))
    return max(steps, 1 if record.decision is not None else 0)


def _evidence_count(record: CaseRecord) -> int:
    if record.proposal is None:
        return 0
    return sum(1 for citation in record.proposal.evidence if citation.verified)


def _item(record: CaseRecord) -> CaseListItem:
    case = record.case
    return CaseListItem(
        id=case.id,
        received_at=case.received_at,
        make=case.make,
        model=case.model,
        year=case.year,
        component=case.component,
        group=case.group,
        status=case.status,
        safety_relevant=case.safety_relevant,
        evidence_count=_evidence_count(record),
        human_touches=_human_touches(record),
    )


def _matches(
    record: CaseRecord,
    *,
    status: CaseStatus | None,
    group: str | None,
    safety: bool | None,
    query: str | None,
) -> bool:
    case = record.case
    if status is not None and case.status != status:
        return False
    if group is not None and case.group != group:
        return False
    if safety is not None and case.safety_relevant != safety:
        return False
    if query:
        needle = query.strip().lower()
        haystack = " ".join(
            (case.id, case.make, case.model, case.component, case.narrative)
        ).lower()
        if needle not in haystack:
            return False
    return True


@router.get("", response_model=CaseListPage)
def list_cases(
    request: Request,
    status: Annotated[CaseStatus | None, Query()] = None,
    group: Annotated[str | None, Query()] = None,
    safety: Annotated[bool | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CaseListPage:
    records = [
        record
        for record in case_records(request)
        if _matches(record, status=status, group=group, safety=safety, query=q)
    ]
    records.sort(key=lambda record: (-record.case.received_at.toordinal(), record.case.id))
    page = records[offset : offset + limit]
    return CaseListPage(
        items=[_item(record) for record in page],
        total=len(records),
        limit=limit,
        offset=offset,
    )


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(request: Request, case_id: str) -> CaseDetail:
    record = find_case(request, case_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"case {case_id} not found")
    evidence = store_of(request).evidence(case_id)
    return CaseDetail(
        case=record.case,
        extraction=record.extraction,
        proposal=record.proposal,
        trace=list(record.trace),
        decision=record.decision,
        similar_cases=list(evidence.similar_cases),
        recalls=list(evidence.recalls),
        investigations=list(evidence.investigations),
    )


@router.get("/{case_id}/trace", response_model=TraceResponse)
def get_trace(request: Request, case_id: str) -> TraceResponse:
    record = find_case(request, case_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"case {case_id} not found")
    return TraceResponse(case_id=case_id, steps=list(record.trace))


@router.post("/{case_id}/decision", response_model=DecisionResponse)
def decide(request: Request, case_id: str, body: DecisionRequest) -> DecisionResponse:
    mode = mode_of(request)
    desk = desk_of(request)
    if mode != "live" or desk is None:
        raise HTTPException(
            status_code=409,
            detail=f"decisions are read-only in {mode} mode",
        )
    edited = body.edited_proposal
    if edited is not None and edited.case_id != case_id:
        raise HTTPException(status_code=400, detail="the edited proposal names a different case")

    before = find_case(request, case_id)
    try:
        record = desk.decide(
            case_id,
            action=body.action,
            rationale=body.rationale,
            edited_proposal=edited,
        )
    except UnknownCaseError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NotAwaitingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidDecisionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    bus = bus_of(request)
    bus.publish("case_status", {"case_id": case_id, "status": record.case.status.value})
    already = len(before.trace) if before is not None else 0
    for step in record.trace[already:]:
        bus.publish("trace", {"case_id": case_id, "step": step.model_dump(mode="json")})

    return DecisionResponse(
        case=record.case,
        trace=list(record.trace),
        pending=None,
        issue_ids=[],
    )
