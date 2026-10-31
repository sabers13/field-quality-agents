"""The LangGraph desk: supervisor, intake, analysis and human checkpoints."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date
from typing import Any, cast
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph._node import StateNode
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from field_quality_agents.agents.analysis import make_analysis_node
from field_quality_agents.agents.budget import budget
from field_quality_agents.agents.finish import finish
from field_quality_agents.agents.gate import human_gate
from field_quality_agents.agents.intake import make_intake_node
from field_quality_agents.agents.model import AgentModel
from field_quality_agents.agents.prompts import AGENTS, load_prompt
from field_quality_agents.agents.safety import safety
from field_quality_agents.agents.simulated_engineer import decide
from field_quality_agents.agents.state import (
    MAX_CHECKPOINTS,
    CaseRun,
    DeskState,
)
from field_quality_agents.agents.supervisor import route, supervisor
from field_quality_agents.agents.tools import ToolRegistry
from field_quality_agents.contracts import Case, HumanDecision, Issue

DeskGraph = CompiledStateGraph[DeskState, None, DeskState, DeskState]
Engineer = Callable[[DeskState], HumanDecision]


def initial_state(case: Case) -> DeskState:
    return {
        "case": case,
        "trace": [],
        "steps": 0,
        "tokens": 0,
        "safety_relevant": case.safety_relevant,
        "issue_ids": [],
    }


def build_desk_graph(
    *,
    tools: ToolRegistry,
    model: AgentModel,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> DeskGraph:
    """Compile the case desk graph.

    ``tools`` is Q2's typed function set (a fake in tests) and ``model`` is Q4's
    chat model behind the small ``AgentModel`` protocol.
    """

    for agent in AGENTS:
        load_prompt(agent)

    builder = StateGraph(DeskState)
    builder.add_node("supervisor", supervisor)
    builder.add_node("intake", cast(StateNode[DeskState, None], make_intake_node(model, tools)))
    builder.add_node("safety", safety)
    builder.add_node("analysis", cast(StateNode[DeskState, None], make_analysis_node(model, tools)))
    builder.add_node("budget", budget)
    builder.add_node("human_gate", human_gate)
    builder.add_node("finish", finish)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route,
        {
            "intake": "intake",
            "safety": "safety",
            "analysis": "analysis",
            "budget": "budget",
            "human_gate": "human_gate",
            "finish": "finish",
        },
    )
    builder.add_edge("intake", "supervisor")
    builder.add_edge("safety", "supervisor")
    builder.add_edge("analysis", "supervisor")
    builder.add_edge("budget", "human_gate")
    builder.add_edge("human_gate", "supervisor")
    builder.add_edge("finish", END)

    saver = checkpointer if checkpointer is not None else InMemorySaver()
    return builder.compile(checkpointer=saver)


def run_case(
    case: Case,
    graph: DeskGraph,
    *,
    engineer: Engineer = decide,
    thread_id: str | None = None,
) -> CaseRun:
    """Run one case to completion, resuming human checkpoints deterministically."""

    config: RunnableConfig = {
        "configurable": {"thread_id": thread_id or f"{case.id}-{uuid4().hex[:12]}"}
    }
    graph.invoke(initial_state(case), config)

    for _ in range(MAX_CHECKPOINTS):
        snapshot = graph.get_state(config)
        if not snapshot.interrupts:
            break
        decision = engineer(cast(DeskState, snapshot.values))
        graph.invoke(Command[HumanDecision](resume=decision), config)

    snapshot = graph.get_state(config)
    values = cast(DeskState, snapshot.values)
    trace = tuple(values.get("trace", []))
    return CaseRun(
        case=values["case"],
        trace=trace,
        extraction=values.get("extraction"),
        proposal=values.get("proposal"),
        decision=values.get("decision"),
        steps=values.get("steps", 0),
        tokens=values.get("tokens", 0),
        budget_hit=any(step.action == "budget_exhausted" for step in trace),
        pending=bool(snapshot.interrupts),
    )


def run_day(
    cases: Sequence[Case],
    until: date,
    graph: DeskGraph,
    *,
    engineer: Engineer = decide,
) -> list[Issue]:
    """Run every case received up to ``until``.

    Opening fleet issues from the day's clusters belongs to Q8's issue agent;
    this function is the Q5 seam and returns no issues.
    """

    runs = [run_case(case, graph, engineer=engineer) for case in cases if case.received_at <= until]
    if any(run.pending for run in runs):
        raise RuntimeError("a case is still waiting for a human decision")
    return []
