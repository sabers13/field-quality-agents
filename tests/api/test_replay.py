"""Recorded-run replay endpoints."""

from __future__ import annotations

from api_fixtures import RUN_ID
from fastapi.testclient import TestClient


def test_runs_are_newest_first(client: TestClient) -> None:
    body = client.get("/api/replay/runs").json()

    assert [item["run_id"] for item in body["items"]] == [RUN_ID, "run-2025-02"]
    assert body["items"][0]["case_count"] == 10
    assert body["items"][0]["status"] == "complete"


def test_events_are_ordered_and_filtered_by_after(client: TestClient) -> None:
    body = client.get(f"/api/replay/runs/{RUN_ID}/events").json()
    assert [item["seq"] for item in body["items"]] == [1, 2, 3]

    later = client.get(f"/api/replay/runs/{RUN_ID}/events", params={"after": 1}).json()
    assert [item["seq"] for item in later["items"]] == [2, 3]
    assert later["items"][0]["kind"] == "trace"
    assert later["items"][0]["case_id"] == "C-2025-0001"


def test_unknown_run_returns_404_and_bad_after_is_rejected(client: TestClient) -> None:
    assert client.get("/api/replay/runs/nope/events").status_code == 404
    assert (
        client.get(f"/api/replay/runs/{RUN_ID}/events", params={"after": "x"}).status_code
        == 422
    )
