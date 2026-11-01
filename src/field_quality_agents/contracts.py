"""Frozen domain contracts shared by the data, agent, API and dashboard lanes.

The shapes in this module are frozen after Q0. A later lane may add a new
optional field only if it does not break existing fixtures; anything else needs
a captain decision recorded in ``reports/DEVIATIONS.md``.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "Case",
    "CaseStatus",
    "Citation",
    "Clue",
    "ClueKind",
    "DecisionAction",
    "DecisionActor",
    "DecisionMemo",
    "EightD",
    "EightDStatus",
    "Extraction",
    "HumanDecision",
    "Issue",
    "IssueStatus",
    "MetricEstimate",
    "Metrics",
    "Proposal",
    "ProposalKind",
    "RunManifest",
    "RunMode",
    "RunStatus",
    "SourceType",
    "TargetedTest",
    "TraceStep",
    "WeekCount",
    "WeeklyReport",
]


class FrozenModel(BaseModel):
    """Base model: immutable, strict about unknown fields, trims strings."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class CaseStatus(StrEnum):
    NEW = "new"
    INTAKE = "intake"
    ANALYSIS = "analysis"
    NEEDS_ENGINEER = "needs_engineer"
    DECIDED = "decided"
    ISSUE_LINKED = "issue_linked"


class ClueKind(StrEnum):
    COMPONENT_GROUP = "component_group"
    SYMPTOM = "symptom"
    CONDITION = "condition"
    FAULT_CODE = "fault_code"
    SAFETY = "safety"
    OTHER = "other"


class ProposalKind(StrEnum):
    STANDARD_TEST = "standard_test"
    TARGETED_LOAD_TEST = "targeted_load_test"
    SAFETY_PRIORITY = "safety_priority"
    EVIDENCE_PACK = "evidence_pack"
    REQUEST_INFO = "request_info"


class DecisionAction(StrEnum):
    APPROVE = "approve"
    OVERRIDE = "override"
    ASK = "ask"
    REQUEST_INFO = "request_info"


class DecisionActor(StrEnum):
    SIMULATED_ENGINEER = "simulated_engineer"
    LIVE_ENGINEER = "live_engineer"


class SourceType(StrEnum):
    CASE = "case"
    RECALL = "recall"
    INVESTIGATION = "investigation"


class IssueStatus(StrEnum):
    OPEN = "open"
    MONITORING = "monitoring"
    CLOSED = "closed"


class EightDStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class RunMode(StrEnum):
    REPLAY = "replay"
    RECORD = "record"
    LIVE = "live"


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class Case(FrozenModel):
    """One incoming report, normalised for both pipelines."""

    id: str = Field(min_length=1)
    received_at: date
    make: str = Field(min_length=1)
    model: str = Field(min_length=1)
    year: int = Field(ge=1886, le=2100)
    component: str = Field(min_length=1)
    narrative: str
    group: str | None = None
    status: CaseStatus = CaseStatus.NEW
    safety_relevant: bool = False
    source: Literal["nhtsa"] = "nhtsa"
    source_id: str | None = None
    mileage: int | None = Field(default=None, ge=0)


class Clue(FrozenModel):
    """A extracted fact and the verbatim span that supports it."""

    kind: ClueKind
    quote: str = Field(min_length=1)


class Extraction(FrozenModel):
    case_id: str = Field(min_length=1)
    group: str = Field(min_length=1)
    summary: str = ""
    symptoms: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    fault_codes: tuple[str, ...] = ()
    clues: tuple[Clue, ...] = ()
    safety_relevant: bool = False


class Citation(FrozenModel):
    source_type: SourceType
    source_id: str = Field(min_length=1)
    quote: str | None = None
    verified: bool = False


class TargetedTest(FrozenModel):
    name: str = Field(min_length=1)
    conditions: tuple[str, ...] = ()
    reason: str = ""


class Proposal(FrozenModel):
    case_id: str = Field(min_length=1)
    kind: ProposalKind
    summary: str = Field(min_length=1)
    rationale: str = ""
    targeted_test: TargetedTest | None = None
    evidence: tuple[Citation, ...] = ()
    requested_info: tuple[str, ...] = ()
    created_at: datetime


class TraceStep(FrozenModel):
    step: int = Field(ge=1)
    agent: str = Field(min_length=1)
    action: str = Field(min_length=1)
    reason: str = ""
    tool: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: dict[str, Any] | None = None
    started_at: datetime
    duration_ms: int = Field(default=0, ge=0)
    tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)


class HumanDecision(FrozenModel):
    case_id: str = Field(min_length=1)
    action: DecisionAction
    actor: DecisionActor
    rationale: str = ""
    decided_at: datetime
    proposal_kind: ProposalKind | None = None
    edited_proposal: Proposal | None = None


class WeekCount(FrozenModel):
    week_start: date
    count: int = Field(ge=0)


class Issue(FrozenModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    opened_at: date
    status: IssueStatus = IssueStatus.OPEN
    make: str
    model: str
    year: int = Field(ge=1886, le=2100)
    group: str
    weekly_counts: tuple[WeekCount, ...] = ()
    observed: int = Field(default=0, ge=0)
    threshold: float = Field(default=0.0, ge=0.0)
    spike_ratio: float = Field(default=0.0, ge=0.0)
    linked_case_ids: tuple[str, ...] = ()
    linked_recall_ids: tuple[str, ...] = ()
    linked_investigation_ids: tuple[str, ...] = ()
    eight_d_id: str | None = None
    memo_id: str | None = None


class EightD(FrozenModel):
    id: str = Field(min_length=1)
    issue_id: str = Field(min_length=1)
    d1_team: tuple[str, ...] = ()
    d2_problem: str = ""
    d3_containment: str = ""
    d4_root_cause_hypotheses: tuple[str, ...] = ()
    citations: tuple[Citation, ...] = ()
    status: EightDStatus = EightDStatus.DRAFT
    created_at: datetime
    updated_at: datetime | None = None


class DecisionMemo(FrozenModel):
    id: str = Field(min_length=1)
    issue_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str = ""
    citations: tuple[Citation, ...] = ()
    created_at: datetime


class MetricEstimate(FrozenModel):
    value: float
    ci_low: float | None = None
    ci_high: float | None = None
    n: int = Field(default=0, ge=0)


class Metrics(FrozenModel):
    """The PLAN §7 metrics for one pipeline over the same cases."""

    cases: int = Field(default=0, ge=0)
    group_macro_f1: MetricEstimate | None = None
    group_coverage: MetricEstimate | None = None
    safety_precision: MetricEstimate | None = None
    safety_recall: MetricEstimate | None = None
    quote_grounding_rate: MetricEstimate | None = None
    quotes_dropped: int | None = Field(default=None, ge=0)
    citation_validity_rate: MetricEstimate | None = None
    targeted_test_share: MetricEstimate | None = None
    targeted_test_with_quote_share: MetricEstimate | None = None
    issue_precision: MetricEstimate | None = None
    issue_median_lead_days: float | None = None
    issue_base_rate: float | None = None
    recall_link_match_rate: MetricEstimate | None = None
    human_touches_per_case: float | None = None
    decided_without_edits_share: float | None = None
    steps_per_case: float | None = None
    cost_per_1000_cases_usd: float | None = None
    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None
    budget_hits: int = Field(default=0, ge=0)
    #: True when the desk saw PLAN §7's evaluation labels, so the metrics that
    #: depend on them are withheld rather than presented as measurements.
    evaluation_labels_in_model_input: bool = False


class WeeklyReport(FrozenModel):
    week_start: date
    week_end: date
    generated_at: datetime
    cases_received: int = Field(default=0, ge=0)
    cases_decided: int = Field(default=0, ge=0)
    cases_needing_engineer: int = Field(default=0, ge=0)
    open_issues: int = Field(default=0, ge=0)
    proposals_targeted_test: int = Field(default=0, ge=0)
    metrics: Metrics = Field(default_factory=Metrics)
    narrative: str = ""


class RunManifest(FrozenModel):
    run_id: str = Field(min_length=1)
    mode: RunMode
    set_name: str = Field(min_length=1)
    started_at: datetime
    completed_at: datetime | None = None
    status: RunStatus = RunStatus.RUNNING
    case_count: int = Field(default=0, ge=0)
    model: str = ""
    prompt_version: str = ""
    seed: int | None = None
    spend_usd: float = Field(default=0.0, ge=0.0)
    steps: int = Field(default=0, ge=0)
    budget_hits: int = Field(default=0, ge=0)
    #: What the desk was allowed to see: "clean", or a legacy policy name that
    #: explains why the evaluation labels were in the recorded requests.
    model_input: str = ""
    record_digest: str = ""
    code_version: str = ""
    files: tuple[str, ...] = ()
