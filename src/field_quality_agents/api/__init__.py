"""The dashboard API: cases, issues, KPIs, replay and live decisions.

Public surface:

- ``create_app`` builds the FastAPI app from a result store and, in live mode,
  a compiled desk graph.
- ``FileResultStore`` reads ``results/runs/<run_id>/``.
- ``MemoryResultStore`` is the fixture store the tests use.
- ``EventBus`` feeds the SSE stream.
"""

from field_quality_agents.api.app import DEFAULT_STATIC_DIR, create_app
from field_quality_agents.api.events import EventBus
from field_quality_agents.api.live import GraphLike, LiveDesk
from field_quality_agents.api.store import (
    CaseEvidence,
    CaseRecord,
    FileResultStore,
    IssueRecord,
    MemoryResultStore,
    MetricsPair,
    ReplayEventRecord,
    ReplayRunRecord,
    ResultStore,
)

__all__ = [
    "DEFAULT_STATIC_DIR",
    "CaseEvidence",
    "CaseRecord",
    "EventBus",
    "FileResultStore",
    "GraphLike",
    "IssueRecord",
    "LiveDesk",
    "MemoryResultStore",
    "MetricsPair",
    "ReplayEventRecord",
    "ReplayRunRecord",
    "ResultStore",
    "create_app",
]
