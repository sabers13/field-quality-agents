"""Fleet issue room endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from field_quality_agents.api.deps import store_of
from field_quality_agents.api.models import IssueDetail, IssuePage, IssueSummary
from field_quality_agents.api.store import IssueRecord
from field_quality_agents.contracts import IssueStatus

__all__ = ["router"]

router = APIRouter(prefix="/api/issues", tags=["issues"])


def _summary(record: IssueRecord) -> IssueSummary:
    issue = record.issue
    return IssueSummary(
        id=issue.id,
        title=issue.title,
        status=issue.status,
        opened_at=issue.opened_at,
        make=issue.make,
        model=issue.model,
        year=issue.year,
        group=issue.group,
        observed=issue.observed,
        threshold=issue.threshold,
        spike_ratio=issue.spike_ratio,
        linked_case_count=len(issue.linked_case_ids),
    )


@router.get("", response_model=IssuePage)
def list_issues(
    request: Request,
    status: Annotated[IssueStatus | None, Query()] = None,
) -> IssuePage:
    records = [
        record
        for record in store_of(request).issues()
        if status is None or record.issue.status == status
    ]
    records.sort(key=lambda record: (-record.issue.opened_at.toordinal(), record.issue.id))
    return IssuePage(items=[_summary(record) for record in records])


@router.get("/{issue_id}", response_model=IssueDetail)
def get_issue(request: Request, issue_id: str) -> IssueDetail:
    record = next(
        (item for item in store_of(request).issues() if item.issue.id == issue_id),
        None,
    )
    if record is None:
        raise HTTPException(status_code=404, detail=f"issue {issue_id} not found")
    issue = record.issue
    return IssueDetail(
        id=issue.id,
        title=issue.title,
        status=issue.status,
        opened_at=issue.opened_at,
        make=issue.make,
        model=issue.model,
        year=issue.year,
        group=issue.group,
        observed=issue.observed,
        threshold=issue.threshold,
        spike_ratio=issue.spike_ratio,
        linked_case_count=len(issue.linked_case_ids),
        weekly_counts=list(issue.weekly_counts),
        linked_case_ids=list(issue.linked_case_ids),
        linked_recall_ids=list(issue.linked_recall_ids),
        linked_investigation_ids=list(issue.linked_investigation_ids),
        eight_d=record.eight_d,
        memo=record.memo,
    )
