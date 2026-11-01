"""PLAN §7 metrics for one agentic run, computed from the run's own records."""

from __future__ import annotations

import random
from collections.abc import Sequence

from field_quality_agents.agents.state import CaseRun
from field_quality_agents.contracts import (
    Case,
    Citation,
    DecisionMemo,
    EightD,
    Issue,
    Metrics,
    Proposal,
)
from field_quality_agents.metrics import (
    Event,
    RecallLink,
    SourceIndex,
    citation_validity,
    estimate,
    group_coverage,
    issue_detection,
    macro_f1,
    quote_grounding,
    recall_link_match_rate,
    safety_scores,
    targeted_test_share,
    targeted_test_with_quote_share,
    workload,
)
from field_quality_agents.tools.models import QuoteVerification

__all__ = ["compute_metrics"]

#: PLAN §5's replay seed, reused for the bootstrap and the issue base rate.
DEFAULT_SEED = 20261031


def _all_citations(
    proposals: Sequence[Proposal],
    eight_d: Sequence[EightD],
    memos: Sequence[DecisionMemo],
) -> list[Citation]:
    citations: list[Citation] = []
    for proposal in proposals:
        citations.extend(proposal.evidence)
    for draft in eight_d:
        citations.extend(draft.citations)
    for memo in memos:
        citations.extend(memo.citations)
    return citations


def _quote_checks(proposals: Sequence[Proposal]) -> list[QuoteVerification]:
    checks: list[QuoteVerification] = []
    for proposal in proposals:
        for citation in proposal.evidence:
            if citation.quote is None:
                continue
            checks.append(
                QuoteVerification(quote=citation.quote, verified=citation.verified)
            )
    return checks


def _recall_links(
    issues: Sequence[Issue],
    events: Sequence[Event],
) -> list[RecallLink]:
    recalls = {
        event.source_id: event
        for event in events
        if event.event_type == "recall"
    }
    links: list[RecallLink] = []
    for issue in issues:
        for recall_id in issue.linked_recall_ids:
            recall = recalls.get(recall_id)
            if recall is None:
                continue
            links.append(
                RecallLink(
                    case_make=issue.make,
                    case_model=issue.model,
                    case_year=issue.year,
                    case_group=issue.group,
                    recall_make=recall.make,
                    recall_model=recall.model,
                    recall_year=recall.year,
                    recall_group=recall.group,
                )
            )
    return links


def compute_metrics(
    *,
    runs: Sequence[CaseRun],
    truth_cases: Sequence[Case],
    proposals: Sequence[Proposal],
    issues: Sequence[Issue],
    eight_d: Sequence[EightD],
    memos: Sequence[DecisionMemo],
    sources: SourceIndex,
    events: Sequence[Event],
    seed: int = DEFAULT_SEED,
) -> Metrics:
    """Return the PLAN §7 numbers for the agentic pipeline."""

    truth_by_id = {case.id: case for case in truth_cases}
    truth_groups = [case.group or "unclear" for case in truth_cases]
    predicted_groups = [
        (run.extraction.group if run.extraction is not None else run.case.group)
        or "unclear"
        for run in runs
    ]
    truth_safety = [
        truth_by_id[run.case.id].safety_relevant
        for run in runs
        if run.case.id in truth_by_id
    ]
    predicted_safety = [
        run.case.safety_relevant for run in runs if run.case.id in truth_by_id
    ]
    safety_precision, safety_recall = safety_scores(truth_safety, predicted_safety)
    issue_stats = issue_detection(
        issues,
        events,
        cases=truth_cases,
        rng=random.Random(seed),
    )
    workload_stats = workload(runs)
    return Metrics(
        cases=len(runs),
        group_macro_f1=macro_f1(
            truth_groups,
            predicted_groups,
            rng=random.Random(seed),
        ),
        group_coverage=group_coverage(predicted_groups, unclear="unclear"),
        safety_precision=safety_precision,
        safety_recall=safety_recall,
        quote_grounding_rate=quote_grounding(_quote_checks(proposals)),
        citation_validity_rate=citation_validity(
            _all_citations(proposals, eight_d, memos),
            sources,
        ),
        targeted_test_share=targeted_test_share(proposals),
        targeted_test_with_quote_share=targeted_test_with_quote_share(proposals),
        issue_precision=(
            estimate(issue_stats["issue_precision"], n=len(issues))
            if issues
            else None
        ),
        issue_median_lead_days=(
            issue_stats["issue_median_lead_days"] if issues else None
        ),
        issue_base_rate=issue_stats["issue_base_rate"] if issues else None,
        recall_link_match_rate=recall_link_match_rate(
            _recall_links(issues, events)
        ),
        human_touches_per_case=workload_stats["human_touches_per_case"],
        decided_without_edits_share=workload_stats["decided_without_edits_share"],
        steps_per_case=workload_stats["steps_per_case"],
        cost_per_1000_cases_usd=workload_stats["cost_per_1000_cases_usd"],
        latency_p50_ms=workload_stats["latency_p50_ms"],
        latency_p95_ms=workload_stats["latency_p95_ms"],
        budget_hits=int(workload_stats["budget_hits"]),
    )
