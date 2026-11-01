"""Shared fixtures for the API tests: in-memory store and a fake graph."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from api_fixtures import FakeGraph, live_graph, make_store
from fastapi import FastAPI
from fastapi.testclient import TestClient

from field_quality_agents.api import create_app
from field_quality_agents.api.store import MemoryResultStore

#: A heartbeat small enough that an SSE test reads it without waiting.
HEARTBEAT_SECONDS = 0.01


@pytest.fixture
def store() -> MemoryResultStore:
    return make_store()


@pytest.fixture
def app(store: MemoryResultStore, tmp_path: Path) -> FastAPI:
    return create_app(store=store, mode="replay", static_dir=tmp_path / "dist")


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def graph() -> FakeGraph:
    return live_graph()


@pytest.fixture
def live_app(store: MemoryResultStore, graph: FakeGraph, tmp_path: Path) -> FastAPI:
    app = create_app(
        store=store,
        graph=graph,
        mode="live",
        static_dir=tmp_path / "dist",
        heartbeat_seconds=HEARTBEAT_SECONDS,
    )
    app.state.desk.start(graph.case)
    return app


@pytest.fixture
def live_client(live_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(live_app) as test_client:
        yield test_client
