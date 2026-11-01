"""Transport models for the dashboard API.

These mirror ``docs/INTERFACES.md`` §Q7 and ``web/src/types.ts``. The domain
objects come from ``contracts.py``; the wrappers here are the JSON shapes the
dashboard reads. Field names are ``snake_case`` and timestamps serialise as ISO
8601.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from field_quality_agents.contracts import (
    Case,
    CaseStatus,
    DecisionAction,
    DecisionMemo,
    EightD,
    Extraction,
    HumanDecision,
    IssueStatus,
    MetricEstimate,
    Metrics,
    Proposal,
    TraceStep,
    WeekCount,
)

__all__ = [
    "CaseDetail",
    "CaseListItem",
    "CaseListPage",
    "CommandCentreData",
    "ComparisonData",
    "ComparisonHeadline",
    "ComparisonRow",
    "ComparisonSummary",
    "DecisionRequest",
    "DecisionResponse",
    "Health",
    "InvestigationRef",
    "IssueDetail",
    "IssuePage",
    "IssueSummary",
    "Kpi",
    "RecallRef",
    "ReplayEvent",
    "ReplayEventPage",
    "ReplayRun",
    "ReplayRunPage",
    "SimilarCaseRef",
    "StreamEvent",
    "Tone",
    "TraceResponse",
]

StreamEventKind = Literal["heartbeat", "case_status", "trace", "issue", "run"]
ReplayEventKind = Literal["case", "trace", "decision", "issue", "report"]
Tone = Literal["neutral", "good", "watch", "issue"]


class ApiModel(BaseModel):
    """Base transport model: explicit fields only, immutable values."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Health(ApiModel):
    status: Literal["ok"]
    mode: str
    version: str


class CaseListItem(ApiModel):
    id: str
    received_at: date
    make: str
    model: str
    year: int
    component: str
    group: str | None = None
    status: CaseStatus
    safety_relevant: bool
    evidence_count: int = 0
    human_touches: int = 0


class CaseListPage(ApiModel):
    items: list[CaseListItem]
    total: int
    limit: int
    offset: int


class SimilarCaseRef(ApiModel):
    id: str
    score: float
    make: str
    model: str
    year: int
    group: str
    excerpt: str


class RecallRef(ApiModel):
    id: str
    summary: str
    open_date: date
    match: bool = True


class InvestigationRef(ApiModel):
    id: str
    summary: str
    open_date: date
    match: bool = True


class CaseDetail(ApiModel):
    case: Case
    extraction: Extraction | None = None
    proposal: Proposal | None = None
    trace: list[TraceStep]
    decision: HumanDecision | None = None
    similar_cases: list[SimilarCaseRef] = []
    recalls: list[RecallRef] = []
    investigations: list[InvestigationRef] = []


class TraceResponse(ApiModel):
    case_id: str
    steps: list[TraceStep]


class DecisionRequest(ApiModel):
    action: DecisionAction
    rationale: str = ""
    edited_proposal: Proposal | None = None


class DecisionResponse(ApiModel):
    case: Case
    trace: list[TraceStep]
    pending: HumanDecision | None = None
    issue_ids: list[str] = []


class IssueSummary(ApiModel):
    id: str
    title: str
    status: IssueStatus
    opened_at: date
    make: str
    model: str
    year: int
    group: str
    observed: int
    threshold: float
    spike_ratio: float
    linked_case_count: int


class IssueDetail(IssueSummary):
    weekly_counts: list[WeekCount]
    linked_case_ids: list[str]
    linked_recall_ids: list[str]
    linked_investigation_ids: list[str]
    eight_d: EightD | None = None
    memo: DecisionMemo | None = None


class IssuePage(ApiModel):
    items: list[IssueSummary]


class Kpi(ApiModel):
    id: str
    label: str
    value: float | int | str
    unit: str | None = None
    context: str
    delta: float | None = None
    tone: Tone | None = None
    series: list[float] | None = None


class ComparisonHeadline(ApiModel):
    id: str
    label: str
    before: float
    after: float
    unit: str


class ComparisonExample(ApiModel):
    case_id: str
    before: str
    after: str
    note: str


class ComparisonSummary(ApiModel):
    headline: list[ComparisonHeadline]
    examples: list[ComparisonExample]


class ComparisonRow(ApiModel):
    metric: str
    label: str
    before: MetricEstimate | float | int | None = None
    after: MetricEstimate | float | int | None = None
    note: str = ""


class ComparisonData(ApiModel):
    before: Metrics
    after: Metrics
    summary: ComparisonSummary
    rows: list[ComparisonRow]


class CommandCentreData(ApiModel):
    window: str
    kpis: list[Kpi]
    live_feed: list[StreamEvent]
    comparison: ComparisonSummary


class StreamEvent(ApiModel):
    id: str | None = None
    kind: StreamEventKind
    at: datetime
    data: dict[str, object]


class ReplayRun(ApiModel):
    run_id: str
    set_name: str
    started_at: datetime
    status: Literal["running", "complete", "failed"]
    case_count: int


class ReplayRunPage(ApiModel):
    items: list[ReplayRun]


class ReplayEvent(ApiModel):
    seq: int
    at: datetime
    kind: ReplayEventKind
    case_id: str | None = None
    issue_id: str | None = None
    payload: dict[str, object] = {}


class ReplayEventPage(ApiModel):
    items: list[ReplayEvent]
