"""Hand-computed fixtures for evidence, test-decision and recall-link metrics."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from field_quality_agents.contracts import (
    Citation,
    Proposal,
    ProposalKind,
    SourceType,
    TargetedTest,
)
from field_quality_agents.metrics import (
    RecallLink,
    SourceIndex,
    citation_validity,
    quote_grounding,
    recall_link_match_rate,
    targeted_test_share,
    targeted_test_with_quote_share,
)
from field_quality_agents.tools.models import QuoteVerification

CREATED = datetime(2025, 1, 2, tzinfo=UTC)


def _proposal(
    kind: ProposalKind,
    *,
    conditions: tuple[str, ...] = (),
    evidence: tuple[Citation, ...] = (),
) -> Proposal:
    return Proposal(
        case_id="C1",
        kind=kind,
        summary="test proposal",
        targeted_test=(
            TargetedTest(name="vibration test", conditions=conditions)
            if kind is ProposalKind.TARGETED_LOAD_TEST
            else None
        ),
        evidence=evidence,
        created_at=CREATED,
    )


def test_quote_grounding_is_the_verified_share() -> None:
    checks = [
        QuoteVerification(quote="a", verified=True),
        QuoteVerification(quote="b", verified=True),
        QuoteVerification(quote="c", verified=True),
        QuoteVerification(quote="d", verified=False),
    ]
    result = quote_grounding(checks)
    assert result.value == 0.75
    assert result.n == 4
    assert result.ci_low is not None and result.ci_low < 0.75 < result.ci_high


def test_citation_validity_checks_ids_and_spans_not_the_flag() -> None:
    sources = SourceIndex(
        cases={"C1": "The battery died at 40,000 miles."},
        recalls={"R1": "Battery cable may corrode."},
    )
    citations = [
        # stale flag false, but the span is present: valid
        Citation(source_type=SourceType.CASE, source_id="C1", quote="battery died", verified=False),
        # id exists, quote does not
        Citation(source_type=SourceType.CASE, source_id="C1", quote="engine exploded"),
        # id does not exist
        Citation(source_type=SourceType.RECALL, source_id="R9", quote=None),
        # id exists, no quote required
        Citation(source_type=SourceType.CASE, source_id="C1", quote=None),
    ]
    result = citation_validity(citations, sources)
    assert result.value == 0.5
    assert result.n == 4


def test_citation_quote_is_whitespace_normalised() -> None:
    sources = SourceIndex(investigations={"I1": "Loss of power steering assist."})
    citations = [
        Citation(
            source_type=SourceType.INVESTIGATION,
            source_id="I1",
            quote="power   steering\nassist",
        )
    ]
    assert citation_validity(citations, sources).value == 1.0


def test_targeted_test_share_uses_test_proposals_only() -> None:
    proposals = [
        _proposal(ProposalKind.STANDARD_TEST),
        _proposal(ProposalKind.STANDARD_TEST),
        _proposal(ProposalKind.STANDARD_TEST),
        _proposal(ProposalKind.TARGETED_LOAD_TEST, conditions=("vibration",)),
        _proposal(ProposalKind.EVIDENCE_PACK),
        _proposal(ProposalKind.REQUEST_INFO),
    ]
    result = targeted_test_share(proposals)
    assert result.value == 0.25
    assert result.n == 4


def test_targeted_test_with_quote_share_needs_conditions_and_a_quote() -> None:
    verified = Citation(
        source_type=SourceType.CASE, source_id="C1", quote="vibration", verified=True
    )
    unverified = Citation(
        source_type=SourceType.CASE, source_id="C1", quote="vibration", verified=False
    )
    proposals = [
        _proposal(
            ProposalKind.TARGETED_LOAD_TEST,
            conditions=("vibration",),
            evidence=(verified,),
        ),
        _proposal(
            ProposalKind.TARGETED_LOAD_TEST,
            conditions=("vibration",),
            evidence=(unverified,),
        ),
    ]
    result = targeted_test_with_quote_share(proposals)
    assert result.value == 0.5
    assert result.n == 2


def test_no_test_proposals_report_zero_with_no_observations() -> None:
    result = targeted_test_share([_proposal(ProposalKind.EVIDENCE_PACK)])
    assert result.value == 0.0
    assert result.n == 0


def test_recall_link_match_rate_requires_all_four_fields() -> None:
    exact = RecallLink(
        case_make="HONDA",
        case_model="ACCORD",
        case_year=2020,
        case_group="lighting",
        recall_make="HONDA",
        recall_model="ACCORD",
        recall_year=2020,
        recall_group="lighting",
    )
    wrong_year = RecallLink(
        case_make="HONDA",
        case_model="ACCORD",
        case_year=2020,
        case_group="lighting",
        recall_make="HONDA",
        recall_model="ACCORD",
        recall_year=2021,
        recall_group="lighting",
    )
    wrong_group = RecallLink(
        case_make="HONDA",
        case_model="ACCORD",
        case_year=2020,
        case_group="lighting",
        recall_make="HONDA",
        recall_model="ACCORD",
        recall_year=2020,
        recall_group="adas",
    )
    result = recall_link_match_rate([exact, wrong_year, wrong_group])
    assert result.value == pytest.approx(1 / 3)
    assert result.n == 3
