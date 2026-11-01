"""Server-sent events for the command centre.

The bus keeps the current run's events in order so a reconnecting browser can
ask for everything after its ``Last-Event-ID``; heartbeats keep idle proxies
and the dashboard's connection indicator honest.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Sequence
from datetime import UTC, datetime

from field_quality_agents.api.models import StreamEvent, StreamEventKind
from field_quality_agents.api.store import ReplayEventRecord, ResultStore

__all__ = [
    "EventBus",
    "feed_from_events",
    "feed_from_store",
    "format_event",
    "format_heartbeat",
    "utcnow",
]


def utcnow() -> datetime:
    return datetime.now(UTC)


def _seq(event: StreamEvent) -> int:
    try:
        return int(event.id or "0")
    except ValueError:
        return 0


class EventBus:
    """An in-process SSE fan-out with a retained window for reconnects."""

    def __init__(self, *, max_events: int = 500, heartbeat_seconds: float = 15.0) -> None:
        self._events: deque[StreamEvent] = deque(maxlen=max_events)
        self._queues: dict[asyncio.Queue[StreamEvent], asyncio.AbstractEventLoop] = {}
        self._seq = 0
        self.heartbeat_seconds = max(0.001, heartbeat_seconds)

    @property
    def last_seq(self) -> int:
        return self._seq

    def publish(
        self,
        kind: StreamEventKind,
        data: dict[str, object],
        *,
        at: datetime | None = None,
    ) -> StreamEvent:
        self._seq += 1
        event = StreamEvent(id=str(self._seq), kind=kind, at=at or utcnow(), data=dict(data))
        self._events.append(event)
        for queue, loop in tuple(self._queues.items()):
            try:
                loop.call_soon_threadsafe(queue.put_nowait, event)
            except RuntimeError:
                # The subscriber's loop closed between the snapshot and here.
                self._queues.pop(queue, None)
        return event

    def retained(self, after: int = 0) -> Sequence[StreamEvent]:
        return tuple(event for event in self._events if _seq(event) > after)

    def recent(self, limit: int = 50) -> Sequence[StreamEvent]:
        return tuple(reversed(tuple(self._events)[-limit:]))

    def subscribe(self) -> tuple[asyncio.Queue[StreamEvent], int]:
        """Register a queue and return it with the sequence already retained."""

        queue: asyncio.Queue[StreamEvent] = asyncio.Queue()
        self._queues[queue] = asyncio.get_running_loop()
        return queue, self._seq

    def unsubscribe(self, queue: asyncio.Queue[StreamEvent]) -> None:
        self._queues.pop(queue, None)


def format_event(event: StreamEvent) -> str:
    payload = event.model_dump_json()
    lines = []
    if event.id is not None:
        lines.append(f"id: {event.id}")
    lines.append(f"event: {event.kind}")
    lines.append(f"data: {payload}")
    return "\n".join(lines) + "\n\n"


def format_heartbeat(at: datetime | None = None) -> str:
    stamp = (at or utcnow()).isoformat().replace("+00:00", "Z")
    return f'event: heartbeat\ndata: {{"at": "{stamp}"}}\n\n'


def feed_from_events(
    events: Sequence[ReplayEventRecord],
    *,
    limit: int = 50,
    run_id: str | None = None,
) -> list[StreamEvent]:
    """Convert recorded replay events into the command centre feed, newest first."""

    feed: list[StreamEvent] = []
    for event in sorted(events, key=lambda item: item.seq):
        feed.append(_stream_event(event, run_id=run_id))
    feed.reverse()
    return feed[:limit]


def _stream_event(event: ReplayEventRecord, *, run_id: str | None = None) -> StreamEvent:
    kind: StreamEventKind
    data: dict[str, object]
    if event.kind == "case":
        kind = "case_status"
        data = {"case_id": event.case_id, "status": event.payload.get("status", "new")}
    elif event.kind == "trace":
        kind = "trace"
        data = {"case_id": event.case_id, "step": event.payload.get("step", {})}
    elif event.kind == "decision":
        kind = "case_status"
        data = {"case_id": event.case_id, "status": event.payload.get("status", "decided")}
    elif event.kind == "issue":
        kind = "issue"
        data = {"issue_id": event.issue_id, "status": event.payload.get("status", "open")}
    else:
        kind = "run"
        data = {
            "run_id": event.payload.get("run_id") or run_id or "",
            "status": "complete",
        }
    return StreamEvent(id=str(event.seq), kind=kind, at=event.at, data=data)


def feed_from_store(store: ResultStore, *, limit: int = 50) -> list[StreamEvent]:
    run_id = store.active_run_id()
    if run_id is None:
        return []
    return feed_from_events(store.replay_events(run_id), limit=limit, run_id=run_id)


def combined_feed(
    store: ResultStore,
    bus: EventBus,
    *,
    limit: int = 50,
) -> list[StreamEvent]:
    """Live events first, then recorded ones, newest first overall."""

    events = list(bus.recent(limit)) + feed_from_store(store, limit=limit)
    events.sort(key=lambda event: (event.at, _seq(event)), reverse=True)
    return events[:limit]
