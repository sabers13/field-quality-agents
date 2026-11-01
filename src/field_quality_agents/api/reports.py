"""KPI, before/after and weekly report endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from field_quality_agents.api.deps import bus_of, store_of
from field_quality_agents.api.events import combined_feed
from field_quality_agents.api.kpis import WindowError, build_command_centre, build_comparison
from field_quality_agents.api.models import CommandCentreData, ComparisonData
from field_quality_agents.contracts import WeeklyReport

__all__ = ["router"]

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/kpis", response_model=CommandCentreData)
def get_kpis(
    request: Request,
    window: Annotated[str, Query()] = "30d",
) -> CommandCentreData:
    store = store_of(request)
    try:
        return build_command_centre(
            store=store,
            window=window,
            feed=combined_feed(store, bus_of(request)),
        )
    except WindowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/comparison", response_model=ComparisonData)
def get_comparison(request: Request) -> ComparisonData:
    store = store_of(request)
    data = build_comparison(store.metrics(), store.comparison_examples())
    if data is None:
        raise HTTPException(status_code=404, detail="no recorded before/after metrics")
    return data


@router.get("/reports/weekly", response_model=WeeklyReport)
def get_weekly_report(
    request: Request,
    week_start: Annotated[date | None, Query()] = None,
) -> WeeklyReport:
    reports = sorted(
        store_of(request).weekly_reports(),
        key=lambda report: (report.week_start, report.week_end),
    )
    match: WeeklyReport | None
    if week_start is None:
        match = reports[-1] if reports else None
    else:
        match = next((report for report in reports if report.week_start == week_start), None)
    if match is None:
        detail = (
            f"no weekly report for {week_start.isoformat()}"
            if week_start is not None
            else "no weekly report was recorded"
        )
        raise HTTPException(status_code=404, detail=detail)
    return match
