"""FastAPI dependencies over ``app.state`` and the live overlay."""

from __future__ import annotations

from typing import Literal, cast

from fastapi import Request

from field_quality_agents.api.events import EventBus
from field_quality_agents.api.live import LiveDesk
from field_quality_agents.api.store import CaseRecord, ResultStore

__all__ = [
    "ApiMode",
    "bus_of",
    "case_records",
    "desk_of",
    "find_case",
    "mode_of",
    "store_of",
]

ApiMode = Literal["live", "replay", "static"]


def store_of(request: Request) -> ResultStore:
    return cast(ResultStore, request.app.state.store)


def mode_of(request: Request) -> ApiMode:
    return cast(ApiMode, request.app.state.mode)


def bus_of(request: Request) -> EventBus:
    return cast(EventBus, request.app.state.bus)


def desk_of(request: Request) -> LiveDesk | None:
    desk = getattr(request.app.state, "desk", None)
    return cast(LiveDesk | None, desk)


def case_records(request: Request) -> list[CaseRecord]:
    """Recorded cases with any live case replacing its recorded copy."""

    records = {record.case.id: record for record in store_of(request).cases()}
    desk = desk_of(request)
    if desk is not None:
        for record in desk.records():
            records[record.case.id] = record
    return list(records.values())


def find_case(request: Request, case_id: str) -> CaseRecord | None:
    desk = desk_of(request)
    if desk is not None:
        live = desk.record(case_id)
        if live is not None:
            return live
    for record in store_of(request).cases():
        if record.case.id == case_id:
            return record
    return None
