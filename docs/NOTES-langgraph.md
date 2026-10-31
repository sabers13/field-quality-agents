# LangGraph and LangChain notes (verified 2026-10-31)

## Versions

Read from PyPI metadata on **2026-10-31**:

| Package | Version | Release date (PyPI) | Python |
|---|---|---|---|
| `langgraph` | 1.2.19 | 2026-10-30 | >=3.10 |
| `langchain` | 1.4.7 | 2026-10-21 | >=3.10 |
| `langchain-core` | 1.7.3 | 2026-10-29 | >=3.10 |
| `langgraph-supervisor` (optional pattern package) | 0.0.31 | (PyPI latest on 2026-10-31) | >=3.10 |

Q5 will pin these versions in `pyproject.toml` when it adds the dependency.

## Sources

| Topic | Source | Checked |
|---|---|---|
| Overview, install, graph basics | <https://docs.langchain.com/oss/python/langgraph/overview> | 2026-10-31 |
| Workflows and agents, routing, orchestrator-worker, tool loops | <https://docs.langchain.com/oss/python/langgraph/workflows-agents> | 2026-10-31 |
| Multi-agent patterns (subagents, handoffs, router) | <https://docs.langchain.com/oss/python/langchain/multi-agent> | 2026-10-31 |
| Tool binding and tool-call loop | <https://docs.langchain.com/oss/python/langchain/models> | 2026-10-31 |
| Persistence and checkpointers | <https://docs.langchain.com/oss/python/langgraph/persistence> | 2026-10-31 |
| Human-in-the-loop `interrupt`/resume | <https://docs.langchain.com/oss/python/langgraph/human-in-the-loop> | 2026-10-31 |

## Graph shape for this project

LangGraph is a low-level orchestration runtime: deterministic nodes and
model-driven nodes live in the same `StateGraph`, with typed state,
conditional edges, durable checkpoints and streaming. The project uses that
shape rather than a single monolithic agent.

For the desk in PLAN §4, the supervisor is an orchestrator node:

- state holds the case, extraction, tool results, proposal, trace, budget
  counters and pending human decision;
- the supervisor applies the fixed safety rule **before** asking the model
  (`safety_relevant -> human`), otherwise it routes to intake, analysis,
  issue, report or a human checkpoint;
- each worker is a node (or a small subgraph) that reads the case state, binds
  only its own tools, appends a `TraceStep`, and returns a state update;
- conditional edges choose the next node from the supervisor's decision;
- the graph ends only at a recorded human decision; no edge may close, scrap,
  return or charge a case.

The two official multi-agent patterns that fit are:

1. **Subagents / orchestrator-worker**: the main supervisor calls specialised
   agents as tools or sends work to worker nodes; all routing passes back
   through the supervisor. This matches the fixed routing policy and audit
   requirement.
2. **Router / handoff**: a routing step classifies the case then hands it to a
   specialist. Useful only if the supervisor's policy becomes a pure
   classifier; it gives less centralised control than subagents.

`langgraph-supervisor` packages the supervisor pattern, but the project can
express it directly with `StateGraph`, `Command` and conditional edges, which
keeps the routing policy in auditable code. Q5 should prefer the direct graph
unless the package removes real complexity.

## Binding tools to an OpenAI-compatible chat model

LangChain chat models expose `bind_tools(tools)`; `tools` are normally
`@tool`-decorated functions (name, docstring and type hints become the JSON
schema). The response is an `AIMessage` whose `.tool_calls` list contains
`{"name", "args", "id"}`. Execute the named tool, append a `ToolMessage` with
the matching `tool_call_id`, and invoke the model again. `ToolNode` is the
prebuilt node for this loop; the project may use it or a small explicit node so
every call and result becomes a `TraceStep`.

For this endpoint, Q4's client owns the raw OpenAI-compatible call and wraps it
as a LangChain-compatible chat model, so `bind_tools` works identically in
record and replay modes. The wrapper must preserve tool-call ids, JSON
arguments and usage, and must raise on a replay miss.

## Human-in-the-loop

`interrupt(value)` inside a node pauses the graph, saves state through the
checkpointer and returns control to the caller. Resume with the same
`thread_id`:

```python
graph.invoke(Command(resume=payload), config={"configurable": {"thread_id": case_id}})
```

Key rules from the docs:

- a checkpointer is required, plus a stable `thread_id` per case;
- the node restarts from its beginning on resume, so side effects before
  `interrupt` must be idempotent;
- do not wrap `interrupt` in a bare `try/except`, and do not conditionally skip
  or reorder interrupts in one node;
- pass JSON-serialisable values only;
- the typed `response_schema` argument (requires `langgraph>=1.2.12`) can
  validate approve/override/ask payloads; Q7's API can reuse that schema;
- in batch runs, Q5's deterministic **simulated engineer** supplies the resume
  value and is labelled simulated; in live mode the dashboard supplies it.

## Checkpointer

Compile with a checkpointer:

```python
from langgraph.checkpoint.memory import InMemorySaver
graph = builder.compile(checkpointer=InMemorySaver())
```

`InMemorySaver` is fine for tests but loses state on restart. For the local
live/replay server Q7 should use `SqliteSaver` (file-based) or `PostgresSaver`
if a database exists; both are documented persistent checkpointers. Checkpoints
are thread-scoped; the case id is the natural `thread_id` (under 255 chars).
Pruning/retention is a Q7/Q9 operational choice.

## Consequences for Q4/Q5

- Q4 must implement a `BaseChatModel`-compatible wrapper, with `bind_tools`,
  `invoke` and usage metadata; record/replay is keyed by
  `sha256(model + prompt version + canonical messages + tools)` per PLAN §3.
- Q5 must keep the supervisor routing policy in code, append a `TraceStep` per
  action, enforce 12 steps / 40k tokens per case, and make the no-close
  property testable.
- Q7 must persist checkpointer state so an approve/override/ask request can
  resume the same thread, and stream actions with SSE.
