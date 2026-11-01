"""The SSE stream: retained events, Last-Event-ID and heartbeats."""

from __future__ import annotations

import httpx
from api_fixtures import CASE_ID
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _until_heartbeat(response: httpx.Response, limit: int = 100) -> list[str]:
    lines: list[str] = []
    for line in response.iter_lines():
        lines.append(line)
        if line == "event: heartbeat" or len(lines) >= limit:
            break
    return lines


def test_stream_opens_with_retry_and_heartbeat(client: TestClient) -> None:
    with client.stream("GET", "/api/events") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        lines = _until_heartbeat(response)

    assert lines[0] == "retry: 3000"
    assert "event: heartbeat" in lines


def test_last_event_id_replays_only_later_events(
    client: TestClient,
    app: FastAPI,
) -> None:
    bus = app.state.bus
    bus.publish("case_status", {"case_id": CASE_ID, "status": "analysis"})
    bus.publish("issue", {"issue_id": "I-1", "status": "open"})

    with client.stream(
        "GET",
        "/api/events",
        headers={"last-event-id": "1"},
    ) as response:
        lines = _until_heartbeat(response)

    event_ids = [line for line in lines if line.startswith("id:")]
    kinds = [line for line in lines if line.startswith("event:")]
    assert event_ids == ["id: 2"]
    assert kinds == ["event: issue", "event: heartbeat"]


def test_decision_publishes_a_case_status_and_trace_event(
    live_client: TestClient,
    live_app: FastAPI,
) -> None:
    response = live_client.post(
        f"/api/cases/{CASE_ID}/decision",
        json={"action": "approve", "rationale": "verified"},
    )
    assert response.status_code == 200

    kinds = [event.kind for event in live_app.state.bus.retained()]
    assert "case_status" in kinds
    assert "trace" in kinds

    with live_client.stream("GET", "/api/events") as stream:
        lines = _until_heartbeat(stream)

    assert "event: case_status" in lines
    assert "event: trace" in lines
