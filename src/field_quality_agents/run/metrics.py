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
from field_quality_agents.tools.quotes import quote_is_grounded

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


def _quote_checks(
    runs: Sequence[CaseRun],
    sources: SourceIndex,
) -> tuple[list[QuoteVerification], int]:
    """Re-check every clue the desk kept and count the ones it dropped.

    The clue text is checked against the case narrative here, not trusted from
    a ``verified`` flag. Quotes the desk dropped are counted from the
    verification steps in the trace, so the share covers everything the model
    proposed rather than only the survivors.
    """

    checks: list[QuoteVerification] = []
    dropped = 0
    for run in runs:
        narrative = sources.cases.get(run.case.id)
        extraction = run.extraction
        if extraction is not None and narrative is not None:
            for clue in extraction.clues:
                checks.append(
                    QuoteVerification(
                        quote=clue.quote,
                        verified=quote_is_grounded(clue.quote, narrative),
                    )
                )
        for step in run.trace:
            if step.tool != "verify_quotes" or not isinstance(step.tool_output, dict):
                continue
            dropped += int(step.tool_output.get("dropped", 0) or 0)
    return checks, dropped


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
    evaluation_labels_in_model_input: bool = False,
) -> Metrics:
    """Return the PLAN §7 numbers for the agentic pipeline.

    ``evaluation_labels_in_model_input`` is honest provenance, not a toggle: it
    reports whether the recorded requests carried PLAN §7's targets. When they
    did, the group and safety numbers measure a copy of the answer key, so they
    are withheld instead of published. Every other metric is unaffected.
    """

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
    checks, dropped = _quote_checks(runs, sources)
    return Metrics(
        cases=len(runs),
        group_macro_f1=(
            None
            if evaluation_labels_in_model_input
            else macro_f1(
                truth_groups,
                predicted_groups,
                rng=random.Random(seed),
            )
        ),
        group_coverage=(
            None
            if evaluation_labels_in_model_input
            else group_coverage(predicted_groups, unclear="unclear")
        ),
        safety_precision=None if evaluation_labels_in_model_input else safety_precision,
        safety_recall=None if evaluation_labels_in_model_input else safety_recall,
        quote_grounding_rate=quote_grounding(checks, dropped=dropped),
        quotes_dropped=dropped,
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
        evaluation_labels_in_model_input=evaluation_labels_in_model_input,
    )
