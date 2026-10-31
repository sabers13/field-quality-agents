"""The agentic desk: a LangGraph case graph with human checkpoints.

Public surface:

- ``build_desk_graph`` compiles the graph from a tool registry and a model.
- ``run_case`` runs one case, resuming checkpoints with the simulated engineer.
- ``run_day`` is the day boundary Q8 calls.
- ``DeskState`` and ``CaseRun`` carry trace, proposal, decision and budgets.
"""

from field_quality_agents.agents.graph import (
    DeskGraph,
    build_desk_graph,
    initial_state,
    run_case,
    run_day,
)
from field_quality_agents.agents.prompts import load_prompt
from field_quality_agents.agents.simulated_engineer import decide
from field_quality_agents.agents.state import (
    MAX_STEPS,
    MAX_TOKENS,
    PROMPT_VERSION,
    CaseRun,
    DeskState,
)
from field_quality_agents.agents.tools import (
    CaseFilters,
    QuoteVerification,
    SimilarCase,
    ToolRegistry,
)

__all__ = [
    "MAX_STEPS",
    "MAX_TOKENS",
    "PROMPT_VERSION",
    "CaseFilters",
    "CaseRun",
    "DeskGraph",
    "DeskState",
    "QuoteVerification",
    "SimilarCase",
    "ToolRegistry",
    "build_desk_graph",
    "decide",
    "initial_state",
    "load_prompt",
    "run_case",
    "run_day",
]
