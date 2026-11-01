"""Issue room, KPIs, before/after comparison and the weekly report."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from api_fixtures import ISSUE_ID
from fastapi.testclient import TestClient

from field_quality_agents.api import create_app
from field_quality_agents.api.models import FinalLiveData, FinalLiveSide
from field_quality_agents.api.store import MemoryResultStore
from field_quality_agents.contracts import MetricEstimate, Metrics


def test_issue_list_and_status_filter(client: TestClient) -> None:
    body = client.get("/api/issues").json()

    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == ISSUE_ID
    assert item["linked_case_count"] == 1
    assert item["spike_ratio"] == 3.5
    assert item["status"] == "open"

    closed = client.get("/api/issues", params={"status": "closed"}).json()
    assert closed["items"] == []


def test_issue_detail_includes_the_8d_draft_and_memo(client: TestClient) -> None:
    body = client.get(f"/api/issues/{ISSUE_ID}").json()

    assert body["weekly_counts"][1]["count"] == 7
    assert body["linked_case_ids"] == ["C-2025-0001"]
    assert body["linked_recall_ids"] == ["R-2024-01"]
    assert body["linked_investigation_ids"] == ["I-2024-02"]
    assert body["eight_d"]["id"] == "8D-1"
    assert body["eight_d"]["status"] == "draft"
    assert body["memo"]["id"] == "M-1"


def test_unknown_issue_returns_404(client: TestClient) -> None:
    assert client.get("/api/issues/nope").status_code == 404


def test_kpis_have_the_seven_plan_tiles(client: TestClient) -> None:
    body = client.get("/api/kpis").json()

    assert body["window"] == "30d"
    ids = [kpi["id"] for kpi in body["kpis"]]
    assert ids == [
        "cases_in",
        "prepared_without_edits",
        "human_touches",
        "time_to_decision",
        "open_issues",
        "cost_per_case",
        "ntf_without_evidence",
    ]
    by_id = {kpi["id"]: kpi for kpi in body["kpis"]}
    assert by_id["cases_in"]["value"] == 2
    assert by_id["open_issues"]["value"] == 1
    assert by_id["human_touches"]["value"] == 2.0
    assert by_id["cost_per_case"]["value"] == 0.012
    assert by_id["cases_in"]["series"] == [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0]


def test_kpi_window_changes_the_case_count(client: TestClient) -> None:
    one_day = client.get("/api/kpis", params={"window": "1d"}).json()

    by_id = {kpi["id"]: kpi for kpi in one_day["kpis"]}
    assert by_id["cases_in"]["value"] == 1
    assert one_day["window"] == "1d"


@pytest.mark.parametrize("window", ["abc", "0d", "400d", "30", "-1d"])
def test_kpi_window_is_validated(client: TestClient, window: str) -> None:
    response = client.get("/api/kpis", params={"window": window})

    assert response.status_code == 400
    assert "window" in response.json()["detail"]


def test_command_centre_feed_is_newest_first(client: TestClient) -> None:
    feed = client.get("/api/kpis").json()["live_feed"]

    assert [event["id"] for event in feed] == ["3", "2", "1"]
    assert feed[0]["kind"] == "issue"
    assert feed[0]["data"]["issue_id"] == ISSUE_ID
    assert feed[1]["kind"] == "trace"
    assert feed[2]["kind"] == "case_status"


def test_comparison_has_rows_both_metrics_and_a_headline(client: TestClient) -> None:
    body = client.get("/api/comparison").json()

    assert body["before"]["cases"] == 10
    assert body["after"]["cases"] == 10
    assert body["rows"]
    headline = {row["id"]: row for row in body["summary"]["headline"]}
    assert headline["human_touches_per_case"]["before"] == 4.0
    assert headline["human_touches_per_case"]["after"] == 2.0
    assert headline["cost_per_1000_cases_usd"]["after"] == 12.0
    assert body["summary"]["examples"][0]["case_id"] == "C-2025-0001"


def test_comparison_returns_404_without_metrics() -> None:
    from field_quality_agents.api import create_app
    from field_quality_agents.api.store import MemoryResultStore

    empty = MemoryResultStore()
    with TestClient(create_app(store=empty, mode="replay", static_dir=None)) as empty_client:
        assert empty_client.get("/api/comparison").status_code == 404
        assert empty_client.get("/api/reports/weekly").status_code == 404
        assert empty_client.get("/api/kpis").status_code == 200


def test_weekly_report_defaults_to_the_latest_week(client: TestClient) -> None:
    body = client.get("/api/reports/weekly").json()

    assert body["week_start"] == "2025-03-10"
    assert body["cases_received"] == 6
    assert body["narrative"] == "The display cluster opened an issue."


def test_weekly_report_can_be_selected_by_week(client: TestClient) -> None:
    body = client.get("/api/reports/weekly", params={"week_start": "2025-03-03"}).json()

    assert body["week_start"] == "2025-03-03"
    assert body["narrative"] == "Earlier week."


def test_weekly_report_unknown_week_returns_404(client: TestClient) -> None:
    response = client.get("/api/reports/weekly", params={"week_start": "2025-01-01"})

    assert response.status_code == 404
    assert "2025-01-01" in response.json()["detail"]


def test_kpis_have_no_final_live_panel_before_q14(client: TestClient) -> None:
    assert client.get("/api/kpis").json()["final_live"] is None


def test_kpis_carry_the_final_live_panel(
    store: MemoryResultStore, tmp_path: Path
) -> None:
    final_metrics = Metrics(
        cases=150,
        safety_precision=MetricEstimate(value=0.5, n=150),
    )
    q9_metrics = Metrics(
        cases=600,
        safety_precision=MetricEstimate(value=0.4, n=600),
    )
    panel = FinalLiveData(
        run_id="final-live",
        set_name="final_live",
        window_start=date(2026, 9, 28),
        window_end=date(2026, 10, 25),
        spend_usd=0.25,
        steps=600,
        budget_hits=0,
        final=FinalLiveSide(cases=150, before=final_metrics, after=final_metrics),
        q9=FinalLiveSide(cases=600, before=q9_metrics, after=q9_metrics),
        q9_run_id="replay",
    )
    app = create_app(
        store=store,
        mode="replay",
        static_dir=tmp_path / "dist",
        final_live=panel,
    )

    with TestClient(app) as test_client:
        body = test_client.get("/api/kpis").json()

    assert body["final_live"]["run_id"] == "final-live"
    assert body["final_live"]["final"]["cases"] == 150
    assert body["final_live"]["q9"]["cases"] == 600
