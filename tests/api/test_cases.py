"""Health and case board endpoints."""

from __future__ import annotations

import pytest
from api_fixtures import CASE_ID, DECIDED_ID, OLD_ID
from fastapi.testclient import TestClient


def test_health_reports_ok_in_replay_mode(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "replay", "version": "0.1.0"}


def test_health_reports_live_mode(live_client: TestClient) -> None:
    assert live_client.get("/api/health").json()["mode"] == "live"


def test_case_list_is_newest_first(client: TestClient) -> None:
    body = client.get("/api/cases").json()

    assert body["total"] == 3
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert [item["id"] for item in body["items"]] == [DECIDED_ID, CASE_ID, OLD_ID]


def test_case_list_filters_by_status_group_and_safety(client: TestClient) -> None:
    by_status = client.get("/api/cases", params={"status": "analysis"}).json()
    by_group = client.get("/api/cases", params={"group": "display"}).json()
    by_safety = client.get("/api/cases", params={"safety": "true"}).json()

    assert [item["id"] for item in by_status["items"]] == [CASE_ID]
    assert {item["id"] for item in by_group["items"]} == {CASE_ID, OLD_ID}
    assert [item["id"] for item in by_safety["items"]] == [DECIDED_ID]


def test_case_list_searches_the_narrative(client: TestClient) -> None:
    body = client.get("/api/cases", params={"q": "brake warning"}).json()

    assert [item["id"] for item in body["items"]] == [DECIDED_ID]
    assert body["total"] == 1


def test_case_list_paginates_and_reports_the_total(client: TestClient) -> None:
    body = client.get("/api/cases", params={"limit": 2, "offset": 1}).json()

    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert [item["id"] for item in body["items"]] == [CASE_ID, OLD_ID]


@pytest.mark.parametrize(
    ("params", "status_code"),
    [
        ({"limit": 0}, 422),
        ({"limit": 500}, 422),
        ({"offset": -1}, 422),
        ({"status": "closed"}, 422),
    ],
)
def test_case_list_rejects_bad_query_parameters(
    client: TestClient, params: dict[str, object], status_code: int
) -> None:
    assert client.get("/api/cases", params=params).status_code == status_code


def test_case_list_item_counts_evidence_and_human_touches(client: TestClient) -> None:
    items = {item["id"]: item for item in client.get("/api/cases").json()["items"]}

    assert items[CASE_ID]["evidence_count"] == 1
    assert items[CASE_ID]["human_touches"] == 0
    assert items[DECIDED_ID]["human_touches"] == 1


def test_case_detail_includes_evidence_and_the_recorded_decision(client: TestClient) -> None:
    body = client.get(f"/api/cases/{CASE_ID}").json()

    assert body["case"]["id"] == CASE_ID
    assert body["extraction"]["summary"] == "Display blanks in the cold"
    assert body["proposal"]["kind"] == "targeted_load_test"
    assert len(body["trace"]) == 3
    assert body["decision"] is None
    assert body["similar_cases"][0]["id"] == "C-2024-0100"
    assert body["similar_cases"][0]["score"] == 0.8123
    assert body["recalls"][0]["match"] is True
    assert body["investigations"][0]["id"] == "I-2024-02"

    decided = client.get(f"/api/cases/{DECIDED_ID}").json()
    assert decided["decision"]["action"] == "approve"
    assert decided["decision"]["actor"] == "simulated_engineer"


def test_case_detail_and_trace_return_404_for_unknown_ids(client: TestClient) -> None:
    assert client.get("/api/cases/nope").status_code == 404
    assert client.get("/api/cases/nope/trace").status_code == 404


def test_trace_endpoint_returns_steps_in_order(client: TestClient) -> None:
    body = client.get(f"/api/cases/{CASE_ID}/trace").json()

    assert body["case_id"] == CASE_ID
    assert [step["step"] for step in body["steps"]] == [1, 2, 3]
    assert body["steps"][0]["agent"] == "supervisor"
