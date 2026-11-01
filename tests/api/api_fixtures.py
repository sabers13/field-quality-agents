"""Fixture data and a fake desk graph for the API tests.

Nothing here touches the network or the committed data: the store is in memory
and the graph is a two-method fake that records ``invoke`` calls.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from langgraph.types import Command

from field_quality_agents.api.models import (
    ComparisonExample,
    InvestigationRef,
    RecallRef,
    SimilarCaseRef,
)
from field_quality_agents.api.store import (
    CaseEvidence,
    CaseRecord,
    IssueRecord,
    MemoryResultStore,
    MetricsPair,
    ReplayEventRecord,
    ReplayRunRecord,
)
from field_quality_agents.contracts import (
    Case,
    CaseStatus,
    Citation,
    Clue,
    ClueKind,
    DecisionAction,
    DecisionActor,
    DecisionMemo,
    EightD,
    EightDStatus,
    Extraction,
    HumanDecision,
    Issue,
    IssueStatus,
    MetricEstimate,
    Metrics,
    Proposal,
    ProposalKind,
    RunManifest,
    RunMode,
    RunStatus,
    SourceType,
    TargetedTest,
    TraceStep,
    WeekCount,
    WeeklyReport,
)

CASE_ID = "C-2025-0001"
DECIDED_ID = "C-2025-0002"
OLD_ID = "C-2024-0009"
ISSUE_ID = "I-2025-0001"
RUN_ID = "run-2025-03"

NOW = datetime(2025, 3, 12, 12, 0, tzinfo=UTC)


def make_case(
    case_id: str = CASE_ID,
    *,
    received_at: date = date(2025, 3, 10),
    status: CaseStatus = CaseStatus.ANALYSIS,
    safety_relevant: bool = False,
    group: str | None = "display",
    narrative: str = "The display goes blank when the cabin is cold.",
    make: str = "Make A",
    model: str = "Model B",
    component: str = "Instrument cluster display",
) -> Case:
    return Case(
        id=case_id,
        received_at=received_at,
        make=make,
        model=model,
        year=2022,
        component=component,
        narrative=narrative,
        group=group,
        status=status,
        safety_relevant=safety_relevant,
    )


def make_extraction(case_id: str = CASE_ID) -> Extraction:
    return Extraction(
        case_id=case_id,
        group="display",
        summary="Display blanks in the cold",
        symptoms=("blank display",),
        conditions=("cold",),
        clues=(Clue(kind=ClueKind.CONDITION, quote="when the cabin is cold"),),
    )


def make_proposal(
    case_id: str = CASE_ID,
    *,
    kind: ProposalKind = ProposalKind.TARGETED_LOAD_TEST,
    verified: bool = True,
) -> Proposal:
    return Proposal(
        case_id=case_id,
        kind=kind,
        summary="Run a cold-soak load test on the cluster",
        rationale="The narrative ties the blank display to cold.",
        targeted_test=TargetedTest(
            name="Cold-soak power cycling",
            conditions=("cold",),
            reason="cold start correlates with the fault",
        ),
        evidence=(
            Citation(
                source_type=SourceType.CASE,
                source_id="C-2024-0100",
                quote="blank below freezing",
                verified=verified,
            ),
        ),
        created_at=NOW,
    )


def make_trace(start: int = 1, count: int = 3, agent: str = "analysis") -> tuple[TraceStep, ...]:
    return tuple(
        TraceStep(
            step=start + index,
            agent=agent if index else "supervisor",
            action=f"fixture:step:{start + index}",
            reason="fixture step",
            started_at=NOW + timedelta(seconds=index),
        )
        for index in range(count)
    )


def make_decision(
    case_id: str = DECIDED_ID,
    *,
    action: DecisionAction = DecisionAction.APPROVE,
    proposal_kind: ProposalKind = ProposalKind.TARGETED_LOAD_TEST,
) -> HumanDecision:
    return HumanDecision(
        case_id=case_id,
        action=action,
        actor=DecisionActor.SIMULATED_ENGINEER,
        rationale="quotes verified",
        decided_at=NOW,
        proposal_kind=proposal_kind,
    )


def make_metrics(*, touches: float, cost: float, targeted: float) -> Metrics:
    return Metrics(
        cases=10,
        group_macro_f1=MetricEstimate(value=0.5, ci_low=0.4, ci_high=0.6, n=10),
        group_coverage=MetricEstimate(value=1.0, ci_low=0.9, ci_high=1.0, n=10),
        safety_precision=MetricEstimate(value=0.5, ci_low=0.3, ci_high=0.7, n=6),
        safety_recall=MetricEstimate(value=0.8, ci_low=0.6, ci_high=0.9, n=5),
        quote_grounding_rate=MetricEstimate(value=0.9, ci_low=0.8, ci_high=1.0, n=20),
        citation_validity_rate=MetricEstimate(value=1.0, ci_low=1.0, ci_high=1.0, n=20),
        targeted_test_share=MetricEstimate(value=targeted, ci_low=0.1, ci_high=0.5, n=10),
        human_touches_per_case=touches,
        decided_without_edits_share=0.5,
        steps_per_case=5.0,
        cost_per_1000_cases_usd=cost,
        latency_p50_ms=100.0,
        latency_p95_ms=200.0,
    )


def make_issue() -> Issue:
    week = date(2025, 3, 3)
    return Issue(
        id=ISSUE_ID,
        title="Display group cluster in Model B",
        opened_at=date(2025, 3, 11),
        status=IssueStatus.OPEN,
        make="Make A",
        model="Model B",
        year=2022,
        group="display",
        weekly_counts=(
            WeekCount(week_start=week, count=2),
            WeekCount(week_start=week + timedelta(weeks=1), count=7),
        ),
        observed=7,
        threshold=2.0,
        spike_ratio=3.5,
        linked_case_ids=(CASE_ID,),
        linked_recall_ids=("R-2024-01",),
        linked_investigation_ids=("I-2024-02",),
        eight_d_id="8D-1",
        memo_id="M-1",
    )


def make_eight_d() -> EightD:
    return EightD(
        id="8D-1",
        issue_id=ISSUE_ID,
        d1_team=("quality engineer", "test engineer"),
        d2_problem="Seven display complaints in two weeks.",
        d3_containment="Quarantine the affected cluster lot.",
        d4_root_cause_hypotheses=("solder fatigue at low temperature",),
        citations=(
            Citation(source_type=SourceType.CASE, source_id=CASE_ID, verified=True),
        ),
        status=EightDStatus.DRAFT,
        created_at=NOW,
    )


def make_memo() -> DecisionMemo:
    return DecisionMemo(
        id="M-1",
        issue_id=ISSUE_ID,
        title="Open a targeted cold-soak test",
        body="The spike holds after reading the linked cases.",
        citations=(
            Citation(source_type=SourceType.CASE, source_id=CASE_ID, verified=True),
        ),
        created_at=NOW,
    )


def make_reports() -> tuple[WeeklyReport, WeeklyReport]:
    return (
        WeeklyReport(
            week_start=date(2025, 3, 3),
            week_end=date(2025, 3, 9),
            generated_at=NOW - timedelta(days=3),
            cases_received=4,
            cases_decided=3,
            open_issues=0,
            narrative="Earlier week.",
        ),
        WeeklyReport(
            week_start=date(2025, 3, 10),
            week_end=date(2025, 3, 16),
            generated_at=NOW,
            cases_received=6,
            cases_decided=5,
            cases_needing_engineer=1,
            open_issues=1,
            proposals_targeted_test=3,
            narrative="The display cluster opened an issue.",
        ),
    )


def make_evidence() -> CaseEvidence:
    return CaseEvidence(
        similar_cases=(
            SimilarCaseRef(
                id="C-2024-0100",
                score=0.8123,
                make="Make A",
                model="Model B",
                year=2021,
                group="display",
                excerpt="The panel blanks below freezing.",
            ),
        ),
        recalls=(
            RecallRef(
                id="R-2024-01",
                summary="Cluster software update",
                open_date=date(2024, 5, 1),
            ),
        ),
        investigations=(
            InvestigationRef(
                id="I-2024-02",
                summary="Display blanking investigation",
                open_date=date(2024, 6, 1),
            ),
        ),
    )


def make_events() -> tuple[ReplayEventRecord, ...]:
    return (
        ReplayEventRecord(
            seq=1,
            at=NOW - timedelta(minutes=3),
            kind="case",
            case_id=CASE_ID,
            payload={"status": "analysis"},
        ),
        ReplayEventRecord(
            seq=2,
            at=NOW - timedelta(minutes=2),
            kind="trace",
            case_id=CASE_ID,
            payload={"step": {"step": 2, "agent": "analysis"}},
        ),
        ReplayEventRecord(
            seq=3,
            at=NOW - timedelta(minutes=1),
            kind="issue",
            issue_id=ISSUE_ID,
            payload={"status": "open"},
        ),
    )


def make_store() -> MemoryResultStore:
    analysis_trace = make_trace(1, 3)
    decided_trace = make_trace(1, 2, agent="human")
    cases = (
        CaseRecord(
            case=make_case(),
            trace=analysis_trace,
            extraction=make_extraction(),
            proposal=make_proposal(),
        ),
        CaseRecord(
            case=make_case(
                DECIDED_ID,
                received_at=date(2025, 3, 12),
                status=CaseStatus.DECIDED,
                safety_relevant=True,
                group="brake electrical",
                narrative="The brake warning lamp flickers and the pedal feels soft.",
                component="ABS control module",
            ),
            trace=decided_trace,
            proposal=make_proposal(DECIDED_ID),
            decision=make_decision(),
        ),
        CaseRecord(
            case=make_case(
                OLD_ID,
                received_at=date(2024, 12, 1),
                status=CaseStatus.NEW,
                narrative="Old report about a radio.",
                component="Radio display",
            ),
        ),
    )
    runs = (
        ReplayRunRecord(
            run_id="run-2025-02",
            set_name="replay_2025",
            started_at=NOW - timedelta(days=11),
            status="complete",
            case_count=5,
        ),
        ReplayRunRecord(
            run_id=RUN_ID,
            set_name="replay_2025",
            started_at=NOW,
            status="complete",
            case_count=10,
        ),
    )
    return MemoryResultStore(
        cases=cases,
        evidence={CASE_ID: make_evidence()},
        issues=(IssueRecord(issue=make_issue(), eight_d=make_eight_d(), memo=make_memo()),),
        runs=runs,
        events={RUN_ID: make_events()},
        weekly_reports=make_reports(),
        metrics=MetricsPair(
            before=make_metrics(touches=4.0, cost=30.0, targeted=0.0),
            after=make_metrics(touches=2.0, cost=12.0, targeted=0.4),
        ),
        comparison_examples=(
            ComparisonExample(
                case_id=CASE_ID,
                before="Standard test, no trouble found",
                after="Targeted cold-soak load test",
                note="The agent used the cold clue.",
            ),
        ),
    )


def make_manifest(run_id: str = RUN_ID) -> RunManifest:
    return RunManifest(
        run_id=run_id,
        mode=RunMode.REPLAY,
        set_name="replay_2025",
        started_at=NOW,
        completed_at=NOW + timedelta(hours=1),
        status=RunStatus.COMPLETE,
        case_count=10,
    )


# --------------------------------------------------------------------------
# Fake graph


@dataclass
class Snapshot:
    values: dict[str, object]
    interrupts: tuple[object, ...] = ()


@dataclass
class FakeGraph:
    """The two methods ``LiveDesk`` calls, with a resumable checkpoint."""

    case: Case
    proposal: Proposal | None = None
    extraction: Extraction | None = None
    trace: list[TraceStep] = field(default_factory=list)
    decision: HumanDecision | None = None
    pending: bool = True
    starts: list[object] = field(default_factory=list)
    resumes: list[HumanDecision] = field(default_factory=list)

    def invoke(self, input: object, config: Mapping[str, object] | None = None) -> object:
        if isinstance(input, Command):
            resume = input.resume
            assert isinstance(resume, HumanDecision)
            self.resumes.append(resume)
            self._apply(resume)
            return self.values
        self.starts.append(input)
        return self.values

    def get_state(self, config: Mapping[str, object]) -> Snapshot:
        return Snapshot(
            values=dict(self.values),
            interrupts=(("checkpoint",) if self.pending else ()),
        )

    @property
    def values(self) -> dict[str, object]:
        return {
            "case": self.case,
            "extraction": self.extraction,
            "proposal": self.proposal,
            "trace": list(self.trace),
            "decision": self.decision,
        }

    def _apply(self, decision: HumanDecision) -> None:
        proposal = decision.edited_proposal or self.proposal
        approved = decision.action in (DecisionAction.APPROVE, DecisionAction.OVERRIDE)
        status = (
            CaseStatus.DECIDED
            if approved and proposal is not None
            else CaseStatus.NEEDS_ENGINEER
        )
        self.case = self.case.model_copy(update={"status": status})
        self.trace = [
            *self.trace,
            TraceStep(
                step=len(self.trace) + 1,
                agent="human",
                action=f"decision:{decision.action.value}",
                reason=decision.rationale,
                started_at=decision.decided_at,
            ),
        ]
        self.proposal = proposal
        self.decision = decision
        self.pending = False


def live_graph() -> FakeGraph:
    return FakeGraph(
        case=make_case(),
        proposal=make_proposal(),
        extraction=make_extraction(),
        trace=list(make_trace(1, 2)),
    )

