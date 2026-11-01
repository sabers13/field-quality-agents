"""Live-mode decision writes: approve, override and ask resume the graph."""

from __future__ import annotations

from api_fixtures import CASE_ID, OLD_ID, FakeGraph, make_proposal
from fastapi import FastAPI
from fastapi.testclient import TestClient

from field_quality_agents.api import create_app
from field_quality_agents.api.store import MemoryResultStore
from field_quality_agents.contracts import DecisionAction, ProposalKind


def test_approve_resumes_the_checkpoint_and_decides_the_case(
    live_client: TestClient,
    live_app: FastAPI,
    graph: FakeGraph,
) -> None:
    response = live_client.post(
        f"/api/cases/{CASE_ID}/decision",
        json={"action": "approve", "rationale": "quotes verified"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["case"]["status"] == "decided"
    assert body["pending"] is None
    assert body["issue_ids"] == []
    assert body["trace"][-1]["agent"] == "human"
    assert body["trace"][-1]["action"] == "decision:approve"

    assert len(graph.resumes) == 1
    assert graph.resumes[0].action is DecisionAction.APPROVE
    assert graph.resumes[0].actor.value == "live_engineer"
    assert live_app.state.desk.awaiting(CASE_ID) is False

    detail = live_client.get(f"/api/cases/{CASE_ID}").json()
    assert detail["case"]["status"] == "decided"
    assert detail["decision"]["actor"] == "live_engineer"


def test_override_uses_the_edited_proposal(live_client: TestClient, graph: FakeGraph) -> None:
    edited = make_proposal(CASE_ID, kind=ProposalKind.STANDARD_TEST)

    response = live_client.post(
        f"/api/cases/{CASE_ID}/decision",
        json={
            "action": "override",
            "rationale": "a standard test is enough",
            "edited_proposal": edited.model_dump(mode="json"),
        },
    )

    assert response.status_code == 200
    assert response.json()["case"]["status"] == "decided"
    assert graph.resumes[0].action is DecisionAction.OVERRIDE
    assert graph.resumes[0].edited_proposal is not None

    detail = live_client.get(f"/api/cases/{CASE_ID}").json()
    assert detail["proposal"]["kind"] == "standard_test"


def test_ask_leaves_the_case_with_an_engineer_and_keeps_the_checkpoint(
    live_client: TestClient,
    live_app: FastAPI,
    graph: FakeGraph,
) -> None:
    response = live_client.post(
        f"/api/cases/{CASE_ID}/decision",
        json={"action": "ask", "rationale": "please attach a photo of the cluster"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["case"]["status"] == "needs_engineer"
    assert body["trace"][-1]["agent"] == "live_engineer"
    assert body["trace"][-1]["action"] == "decision:ask"
    assert graph.resumes == []
    assert live_app.state.desk.awaiting(CASE_ID) is True

    detail = live_client.get(f"/api/cases/{CASE_ID}").json()
    assert detail["case"]["status"] == "needs_engineer"
    assert detail["decision"] is None

    approved = live_client.post(
        f"/api/cases/{CASE_ID}/decision",
        json={"action": "approve", "rationale": "photo arrived"},
    )
    assert approved.status_code == 200
    assert approved.json()["case"]["status"] == "decided"
    actions = [step["action"] for step in approved.json()["trace"]]
    assert "decision:ask" in actions


def test_replay_mode_refuses_to_write(client: TestClient) -> None:
    response = client.post(
        f"/api/cases/{CASE_ID}/decision",
        json={"action": "approve", "rationale": "should not work"},
    )

    assert response.status_code == 409
    assert "read-only" in response.json()["detail"]


def test_live_mode_without_a_graph_refuses_to_write(store: MemoryResultStore) -> None:
    app = create_app(store=store, mode="live", static_dir=None)
    with TestClient(app) as client:
        response = client.post(
            f"/api/cases/{CASE_ID}/decision",
            json={"action": "approve", "rationale": "no graph"},
        )

    assert response.status_code == 409


def test_unknown_case_and_finished_checkpoint_return_404_and_409(
    live_client: TestClient,
) -> None:
    unknown = live_client.post(
        f"/api/cases/{OLD_ID}/decision",
        json={"action": "approve", "rationale": "not started"},
    )
    assert unknown.status_code == 404

    first = live_client.post(
        f"/api/cases/{CASE_ID}/decision",
        json={"action": "approve", "rationale": "done"},
    )
    assert first.status_code == 200

    again = live_client.post(
        f"/api/cases/{CASE_ID}/decision",
        json={"action": "approve", "rationale": "already decided"},
    )
    assert again.status_code == 409


def test_edited_proposal_must_name_the_same_case(live_client: TestClient) -> None:
    edited = make_proposal("another-case")

    response = live_client.post(
        f"/api/cases/{CASE_ID}/decision",
        json={
            "action": "override",
            "rationale": "wrong case",
            "edited_proposal": edited.model_dump(mode="json"),
        },
    )

    assert response.status_code == 400


def test_decision_body_is_validated(live_client: TestClient) -> None:
    response = live_client.post(
        f"/api/cases/{CASE_ID}/decision",
        json={"rationale": "missing action"},
    )

    assert response.status_code == 422
