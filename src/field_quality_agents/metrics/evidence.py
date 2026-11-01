"""Evidence metrics: quote grounding, citation validity, tests and recall links.

Everything here is a pure function over already-collected records. Nothing
opens a file, calls a tool or grades with a model; PLAN §2.5 requires that.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from field_quality_agents.contracts import (
    Citation,
    MetricEstimate,
    Proposal,
    ProposalKind,
    SourceType,
)
from field_quality_agents.metrics.estimates import estimate, wilson_interval
from field_quality_agents.tools.models import QuoteVerification
from field_quality_agents.tools.quotes import quote_is_grounded

__all__ = [
    "RecallLink",
    "SourceIndex",
    "citation_validity",
    "quote_grounding",
    "recall_link_match_rate",
    "targeted_test_share",
    "targeted_test_with_quote_share",
]


@dataclass(frozen=True)
class SourceIndex:
    """The text each citable id resolves to, split by source type.

    The API layer builds this from the committed parquet (or a fixture). A
    citation is valid only when its id appears here; a quoted span must also be
    found verbatim after whitespace normalisation.
    """

    cases: Mapping[str, str] = field(default_factory=dict)
    recalls: Mapping[str, str] = field(default_factory=dict)
    investigations: Mapping[str, str] = field(default_factory=dict)

    def text_for(self, source_type: SourceType, source_id: str) -> str | None:
        if source_type is SourceType.CASE:
            return self.cases.get(source_id)
        if source_type is SourceType.RECALL:
            return self.recalls.get(source_id)
        return self.investigations.get(source_id)


def quote_grounding(checks: Sequence[QuoteVerification], *, dropped: int = 0) -> MetricEstimate:
    """Share of the quotes the model proposed that were found verbatim.

    ``dropped`` counts quotes the desk rejected, which never reach ``checks``:
    they stay in the denominator, or the share would measure the survivors.
    """

    n = len(checks) + dropped
    successes = sum(1 for check in checks if check.verified)
    low, high = wilson_interval(successes, n)
    return estimate(successes / n if n else 0.0, ci_low=low, ci_high=high, n=n)


def citation_validity(citations: Sequence[Citation], sources: SourceIndex) -> MetricEstimate:
    """Share of citations whose id exists and whose quote is in that source.

    The citation's own ``verified`` flag is deliberately ignored: this metric
    re-checks the source, so a stale flag cannot inflate it.
    """

    n = len(citations)
    valid = 0
    for citation in citations:
        text = sources.text_for(citation.source_type, citation.source_id)
        if text is None:
            continue
        if citation.quote is None:
            valid += 1
            continue
        if quote_is_grounded(citation.quote, text):
            valid += 1
    low, high = wilson_interval(valid, n)
    return estimate(valid / n if n else 0.0, ci_low=low, ci_high=high, n=n)


_TEST_KINDS = frozenset({ProposalKind.STANDARD_TEST, ProposalKind.TARGETED_LOAD_TEST})

#: A condition word is a token long enough to mean something: "cold", "moisture".
_CONDITION_TOKEN = re.compile(r"[0-9A-Za-z]{4,}")


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _CONDITION_TOKEN.findall(text)}


def _same_word(left: str, right: str) -> bool:
    """A condition word matches its own inflection ("vibration"/"vibrates")."""

    if left == right:
        return True
    return min(len(left), len(right)) >= 5 and left[:5] == right[:5]


def targeted_test_share(proposals: Sequence[Proposal]) -> MetricEstimate:
    """Share of test proposals that ask for a targeted load test.

    Evidence packs and information requests are not test decisions and are not
    in the denominator.
    """

    test_proposals = [proposal for proposal in proposals if proposal.kind in _TEST_KINDS]
    n = len(test_proposals)
    targeted = sum(
        1 for proposal in test_proposals if proposal.kind is ProposalKind.TARGETED_LOAD_TEST
    )
    low, high = wilson_interval(targeted, n)
    return estimate(targeted / n if n else 0.0, ci_low=low, ci_high=high, n=n)


def targeted_test_with_quote_share(proposals: Sequence[Proposal]) -> MetricEstimate:
    """Share of targeted tests whose condition is supported by a verified quote.

    PLAN §7 asks for a test that "carries a condition with a verified quote".
    A quote anywhere in the proposal is not enough: the quoted span must share
    a condition word with the test, or the test and its evidence could be about
    different things.
    """

    targeted = [
        proposal for proposal in proposals if proposal.kind is ProposalKind.TARGETED_LOAD_TEST
    ]
    n = len(targeted)
    grounded = 0
    for proposal in targeted:
        test = proposal.targeted_test
        conditions = test.conditions if test is not None else ()
        condition_tokens: set[str] = set()
        for condition in conditions:
            condition_tokens |= _tokens(condition)
        if not condition_tokens:
            continue
        if any(
            citation.verified
            and citation.quote is not None
            and any(
                _same_word(quoted, condition)
                for quoted in _tokens(citation.quote)
                for condition in condition_tokens
            )
            for citation in proposal.evidence
        ):
            grounded += 1
    low, high = wilson_interval(grounded, n)
    return estimate(grounded / n if n else 0.0, ci_low=low, ci_high=high, n=n)


@dataclass(frozen=True)
class RecallLink:
    """One recalled part proposed as evidence for one case."""

    case_make: str
    case_model: str
    case_year: int
    case_group: str
    recall_make: str
    recall_model: str
    recall_year: int | None
    recall_group: str | None


def recall_link_match_rate(links: Sequence[RecallLink]) -> MetricEstimate:
    """Share of linked recalls matching make, model, year and group."""

    n = len(links)
    matches = sum(
        1
        for link in links
        if link.case_make == link.recall_make
        and link.case_model == link.recall_model
        and link.recall_year == link.case_year
        and link.recall_group == link.case_group
    )
    low, high = wilson_interval(matches, n)
    return estimate(matches / n if n else 0.0, ci_low=low, ci_high=high, n=n)
