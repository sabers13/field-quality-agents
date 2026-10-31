from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

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
    Extraction,
    HumanDecision,
    Issue,
    MetricEstimate,
    Metrics,
    Proposal,
    ProposalKind,
    RunManifest,
    RunMode,
    SourceType,
    TargetedTest,
    TraceStep,
    WeekCount,
    WeeklyReport,
)

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


def make_case() -> Case:
    return Case(
        id="case-1",
        received_at=date(2026, 10, 1),
        make="Example",
        model="One",
        year=2024,
        component="WIRING",
        narrative="Intermittent wiper failure in rain.",
        group="electrical",
        safety_relevant=True,
    )


def test_case_round_trip_and_enum_values() -> None:
    case = make_case()
    assert case.status is CaseStatus.NEW
    payload = case.model_dump(mode="json")
    assert payload["status"] == "new"
    assert Case.model_validate(payload) == case


def test_contracts_are_frozen() -> None:
    case = make_case()
    with pytest.raises(ValidationError, match="frozen"):
        case.status = CaseStatus.DECIDED


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Case.model_validate({**make_case().model_dump(), "unexpected": True})


def test_all_q0_contracts_instantiate() -> None:
    clue = Clue(kind=ClueKind.SYMPTOM, quote="wiper failure")
    extraction = Extraction(
        case_id="case-1",
        group="electrical",
        summary="Wiper failure",
        symptoms=("wiper failure",),
        clues=(clue,),
        safety_relevant=True,
    )
    citation = Citation(
        source_type=SourceType.CASE,
        source_id="case-1",
        quote="wiper failure",
        verified=True,
    )
    proposal = Proposal(
        case_id="case-1",
        kind=ProposalKind.TARGETED_LOAD_TEST,
        summary="Run a wet-cycle load test",
        rationale="Moisture is a plausible condition.",
        targeted_test=TargetedTest(
            name="humidity/condensation test",
            conditions=("rain",),
            reason="Water ingress",
        ),
        evidence=(citation,),
        created_at=NOW,
    )
    step = TraceStep(
        step=1,
        agent="analysis",
        action="search similar cases",
        reason="Find prior reports",
        tool="similar_cases",
        tool_input={"text": "wiper failure", "k": 5},
        tool_output={"count": 2},
        started_at=NOW,
        duration_ms=120,
        tokens=400,
        cost_usd=0.0001,
    )
    decision = HumanDecision(
        case_id="case-1",
        action=DecisionAction.APPROVE,
        actor=DecisionActor.SIMULATED_ENGINEER,
        rationale="Quote verified.",
        decided_at=NOW,
        proposal_kind=proposal.kind,
        edited_proposal=None,
    )
    week = WeekCount(week_start=date(2026, 10, 5), count=4)
    issue = Issue(
        id="issue-1",
        title="Wiper cluster",
        opened_at=date(2026, 10, 10),
        make="Example",
        model="One",
        year=2024,
        group="electrical",
        weekly_counts=(week,),
        observed=4,
        threshold=3.0,
        spike_ratio=1.33,
        linked_case_ids=("case-1",),
        linked_recall_ids=("recall-1",),
        linked_investigation_ids=("inv-1",),
        eight_d_id="8d-1",
        memo_id="memo-1",
    )
    eight_d = EightD(
        id="8d-1",
        issue_id="issue-1",
        d1_team=("quality engineer",),
        d2_problem="Repeated wiper reports.",
        d3_containment="Inspect stock.",
        d4_root_cause_hypotheses=("Water ingress",),
        citations=(citation,),
        created_at=NOW,
    )
    memo = DecisionMemo(
        id="memo-1",
        issue_id="issue-1",
        title="Open an issue",
        body="Evidence supports an issue.",
        citations=(citation,),
        created_at=NOW,
    )
    metrics = Metrics(
        cases=1,
        group_macro_f1=MetricEstimate(value=0.8, ci_low=0.7, ci_high=0.9, n=1),
        budget_hits=0,
    )
    report = WeeklyReport(
        week_start=date(2026, 10, 5),
        week_end=date(2026, 10, 11),
        generated_at=NOW,
        cases_received=1,
        cases_decided=1,
        metrics=metrics,
        narrative="One case.",
    )
    manifest = RunManifest(
        run_id="run-1",
        mode=RunMode.REPLAY,
        set_name="replay_2025",
        started_at=NOW,
        completed_at=NOW,
        case_count=1,
    )

    assert extraction.clues[0].kind is ClueKind.SYMPTOM
    assert proposal.targeted_test is not None
    assert step.tool == "similar_cases"
    assert decision.action is DecisionAction.APPROVE
    assert issue.weekly_counts[0].count == 4
    assert eight_d.d4_root_cause_hypotheses == ("Water ingress",)
    assert memo.issue_id == "issue-1"
    assert report.metrics.group_macro_f1 is not None
    assert manifest.mode is RunMode.REPLAY
    assert metrics.model_dump(mode="json")["budget_hits"] == 0
