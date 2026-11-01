"""Replay endpoints: recorded runs and their ordered events."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from field_quality_agents.api.deps import store_of
from field_quality_agents.api.models import ReplayEvent, ReplayEventPage, ReplayRun, ReplayRunPage

__all__ = ["router"]

router = APIRouter(prefix="/api/replay", tags=["replay"])


@router.get("/runs", response_model=ReplayRunPage)
def list_runs(request: Request) -> ReplayRunPage:
    runs = sorted(
        store_of(request).runs(),
        key=lambda run: (run.started_at, run.run_id),
        reverse=True,
    )
    return ReplayRunPage(
        items=[
            ReplayRun(
                run_id=run.run_id,
                set_name=run.set_name,
                started_at=run.started_at,
                status=run.status,
                case_count=run.case_count,
            )
            for run in runs
        ]
    )


@router.get("/runs/{run_id}/events", response_model=ReplayEventPage)
def list_events(
    request: Request,
    run_id: str,
    after: Annotated[int, Query(ge=0)] = 0,
) -> ReplayEventPage:
    store = store_of(request)
    if not any(run.run_id == run_id for run in store.runs()):
        raise HTTPException(status_code=404, detail=f"run {run_id} not found")
    events = sorted(
        (event for event in store.replay_events(run_id) if event.seq > after),
        key=lambda event: event.seq,
    )
    return ReplayEventPage(
        items=[
            ReplayEvent(
                seq=event.seq,
                at=event.at,
                kind=event.kind,
                case_id=event.case_id,
                issue_id=event.issue_id,
                payload=event.payload,
            )
            for event in events
        ]
    )
