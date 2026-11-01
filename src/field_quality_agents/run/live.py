"""Build a live dashboard over a recorded run and its recordings.

This is the wiring the Q8 end-to-end test uses: ``fqa serve --mode live``
serves the recorded case board, starts the desk graph for the cases that are
not yet decided (using the recorded tool outputs and model turns), and lets the
dashboard's approve/override/ask buttons resume the graph checkpoints.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from field_quality_agents.agents.graph import build_desk_graph
from field_quality_agents.api import create_app
from field_quality_agents.api.store import FileResultStore
from field_quality_agents.contracts import Case
from field_quality_agents.llm.langchain_model import LangChainChatModel
from field_quality_agents.llm.prices import DEFAULT_MODEL
from field_quality_agents.llm.recorder import RecordReplayStore
from field_quality_agents.run.tools import ReplayTools
from field_quality_agents.run.writer import read_json

__all__ = ["build_live_app"]


def _tool_outputs(run_dir: Path) -> dict[str, object]:
    path = run_dir / "tool_outputs.json"
    if not path.is_file():
        return {}
    raw = read_json(path)
    return raw if isinstance(raw, dict) else {}


def _input_cases(run_dir: Path, store: FileResultStore) -> list[Case]:
    path = run_dir / "input_cases.json"
    if not path.is_file():
        return [record.case for record in store.cases()]
    raw = read_json(path)
    if not isinstance(raw, list):
        return [record.case for record in store.cases()]
    return [Case.model_validate(item) for item in raw]


def build_live_app(
    *,
    results_dir: str | Path = "results/runs",
    run_id: str | None = None,
    recordings_dir: str | Path = "recordings",
    static_dir: str | Path | None = "web/dist",
    heartbeat_seconds: float = 15.0,
    live_limit: int = 25,
) -> FastAPI:
    """Create the live app and start up to ``live_limit`` case threads."""

    root = Path(results_dir)
    store = FileResultStore(root, run_id=run_id)
    active = store.active_run_id()
    if active is None:
        raise ValueError(f"no recorded run under {root}")
    tools = ReplayTools(_tool_outputs(root / active))
    model = LangChainChatModel(
        store=RecordReplayStore(Path(recordings_dir), "replay"),
        model=DEFAULT_MODEL,
    )
    graph = build_desk_graph(tools=tools, model=model)
    app = create_app(
        store=store,
        graph=graph,
        mode="live",
        static_dir=static_dir,
        heartbeat_seconds=heartbeat_seconds,
    )
    desk = app.state.desk
    started = 0
    final_cases = {record.case.id: record.case for record in store.cases()}
    for case in _input_cases(root / active, store):
        if started >= live_limit:
            desk.track(final_cases.get(case.id, case))
            continue
        tools.current_case_id = case.id
        try:
            desk.start(case)
        except Exception:
            # A recording miss should not take the whole dashboard down; the
            # case stays visible and read-only.
            desk.track(final_cases.get(case.id, case))
            continue
        started += 1
    return app
