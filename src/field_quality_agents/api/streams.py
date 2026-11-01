"""The command centre's server-sent event stream."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from field_quality_agents.api.deps import bus_of
from field_quality_agents.api.events import EventBus, format_event, format_heartbeat
from field_quality_agents.api.models import StreamEvent

__all__ = ["router"]

router = APIRouter(prefix="/api", tags=["stream"])

_HEADERS = {
    "cache-control": "no-cache",
    "connection": "keep-alive",
    "x-accel-buffering": "no",
}


def _seq(event: StreamEvent) -> int:
    try:
        return int(event.id or "0")
    except ValueError:
        return 0


async def _stream(bus: EventBus, after: int) -> AsyncIterator[str]:
    queue, current = bus.subscribe()
    sent = after
    try:
        yield "retry: 3000\n\n"
        for event in bus.retained(after):
            if _seq(event) > current:
                continue
            sent = max(sent, _seq(event))
            yield format_event(event)
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=bus.heartbeat_seconds)
            except TimeoutError:
                yield format_heartbeat()
                continue
            if _seq(event) > sent:
                sent = _seq(event)
                yield format_event(event)
    finally:
        bus.unsubscribe(queue)


def _after(request: Request) -> int:
    raw = request.headers.get("last-event-id") or request.query_params.get("after") or "0"
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


@router.get("/events")
async def stream_events(request: Request) -> StreamingResponse:
    return StreamingResponse(
        _stream(bus_of(request), _after(request)),
        media_type="text/event-stream",
        headers=_HEADERS,
    )
