"""FastAPI application factory for the dashboard backend.

``fqa serve`` builds a replay app over ``results/runs``; Q8/Q9's live wiring
passes a compiled desk graph and ``mode="live"``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from field_quality_agents import __version__
from field_quality_agents.api import cases, issues, replay, reports, streams
from field_quality_agents.api.deps import ApiMode
from field_quality_agents.api.events import EventBus
from field_quality_agents.api.live import GraphLike, LiveDesk
from field_quality_agents.api.models import Health
from field_quality_agents.api.static import add_static_routes
from field_quality_agents.api.store import ResultStore

__all__ = ["DEFAULT_STATIC_DIR", "create_app"]

#: The Vite dev server's usual origins; the built dashboard is same-origin.
DEV_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)

#: Built dashboard output, relative to the repository root.
DEFAULT_STATIC_DIR = Path("web/dist")


def create_app(
    *,
    store: ResultStore,
    graph: GraphLike | None = None,
    mode: ApiMode = "replay",
    static_dir: str | Path | None = None,
    heartbeat_seconds: float = 15.0,
) -> FastAPI:
    """Build the API app.

    ``store`` is read-only recorded data (``FileResultStore`` in production, a
    fixture store in tests). ``graph`` is only used in live mode. The two extra
    keyword arguments beyond ``docs/INTERFACES.md`` are additive: the static
    directory and the SSE heartbeat interval.
    """

    app = FastAPI(
        title="field-quality-agents",
        version=__version__,
        description="Recorded and live views of the agentic returns desk.",
    )
    app.state.store = store
    app.state.mode = mode
    app.state.bus = EventBus(heartbeat_seconds=heartbeat_seconds)
    app.state.desk = LiveDesk(graph) if mode == "live" and graph is not None else None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(DEV_ORIGINS),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=Health, tags=["health"])
    def health() -> Health:
        return Health(status="ok", mode=mode, version=__version__)

    app.include_router(cases.router)
    app.include_router(issues.router)
    app.include_router(reports.router)
    app.include_router(replay.router)
    app.include_router(streams.router)
    add_static_routes(app, Path(static_dir) if static_dir is not None else DEFAULT_STATIC_DIR)
    return app
