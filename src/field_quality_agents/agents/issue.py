"""Issue agent: turn a fleet spike into a cited issue, 8D draft and memo.

PLAN §4 runs this agent after each simulated day over the cases received so
far. It calls ``cluster_stats`` for every recent vehicle/group key, opens one
issue per key while the Poisson spike holds, links the matching recalls and
investigations, and drafts 8D D1-D4 plus a one-page decision memo.

The drafts are deterministic: every figure comes from the cluster statistics
and the linked ids, and :func:`checked_citations` re-validates every citation
against the sources in code before an issue is returned. A statement without a
citation is rejected rather than written.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol

from field_quality_agents.contracts import (
    Case,
    Citation,
    DecisionMemo,
    EightD,
    Issue,
    IssueStatus,
    SourceType,
)
from field_quality_agents.metrics.evidence import SourceIndex
from field_quality_agents.tools.models import ClusterStats

__all__ = [
    "CitationError",
    "IssueAgentResult",
    "IssueDraft",
    "IssueTools",
    "UncitedStatementError",
    "checked_citations",
    "review_day",
]

#: A spike must be supported by at least this many replay cases in the window
#: before the agent opens an issue. The fleet series can include reports that
#: are not in the replay set, so the linked cases are the readable evidence.
MIN_LINKED_CASES = 2

#: How far back the agent reads cases when it explains a spike.
LOOKBACK_DAYS = 28

#: How many case ids one 8D or memo cites; keeps the draft readable.
MAX_CITED_CASES = 4


class CitationError(ValueError):
    """A citation names an id or quote that is not in the source index."""


class UncitedStatementError(ValueError):
    """An 8D or memo statement has no case, recall or investigation id."""


class IssueTools(Protocol):
    """The fleet tools the issue agent calls (Q2's typed functions)."""

    def cluster_stats(
        self,
        make: str,
        model: str,
        year: int,
        group: str,
        until_date: date,
    ) -> ClusterStats: ...

    def recalls_for(
        self, make: str, model: str, year: int, group: str
    ) -> list[dict[str, object]]: ...

    def investigations_for(
        self, make: str, model: str, year: int, group: str
    ) -> list[dict[str, object]]: ...


@dataclass(frozen=True)
class IssueDraft:
    """One opened issue with the documents drafted for it."""

    issue: Issue
    eight_d: EightD
    memo: DecisionMemo


@dataclass(frozen=True)
class IssueAgentResult:
    """Everything the issue agent produced for one simulated day."""

    drafts: tuple[IssueDraft, ...] = ()

    @property
    def issues(self) -> tuple[Issue, ...]:
        return tuple(draft.issue for draft in self.drafts)

    @property
    def eight_d(self) -> tuple[EightD, ...]:
        return tuple(draft.eight_d for draft in self.drafts)

    @property
    def memos(self) -> tuple[DecisionMemo, ...]:
        return tuple(draft.memo for draft in self.drafts)


def _normalise(text: str) -> str:
    return " ".join(text.split())


def _citation_is_valid(citation: Citation, sources: SourceIndex) -> bool:
    text = sources.text_for(citation.source_type, citation.source_id)
    if text is None:
        return False
    if citation.quote is None:
        return True
    return _normalise(citation.quote) in _normalise(text)


def checked_citations(
    citations: Iterable[Citation],
    sources: SourceIndex,
) -> tuple[Citation, ...]:
    """Return the citations with ``verified`` set, or raise on an invalid one.

    This is the code-level check PLAN §4 and §7 require: an id must resolve in
    the source index, and a quoted span must be found in that source.
    """

    checked: list[Citation] = []
    for citation in citations:
        if not _citation_is_valid(citation, sources):
            raise CitationError(
                f"citation {citation.source_type.value}:{citation.source_id} "
                "does not resolve to its source"
            )
        checked.append(citation.model_copy(update={"verified": True}))
    return tuple(checked)


def _ensure_cited(statement: str, ids: Sequence[str]) -> str:
    if not any(identifier in statement for identifier in ids):
        raise UncitedStatementError(f"statement has no citation: {statement!r}")
    return statement


def _at(day: date, hour: int, offset: int = 0) -> datetime:
    return datetime.combine(day, time(hour, 0), tzinfo=UTC) + timedelta(seconds=offset)


def _case_citations(cases: Sequence[Case]) -> tuple[Citation, ...]:
    return tuple(
        Citation(source_type=SourceType.CASE, source_id=case.id, verified=False)
        for case in cases
    )


def _event_citations(
    source_type: SourceType,
    rows: Sequence[dict[str, object]],
) -> tuple[Citation, ...]:
    citations: list[Citation] = []
    for row in rows:
        identifier = row.get("id")
        if isinstance(identifier, str) and identifier:
            citations.append(
                Citation(source_type=source_type, source_id=identifier, verified=False)
            )
    return tuple(citations)


def _source_index(
    cases: Sequence[Case],
    recalls: Sequence[dict[str, object]],
    investigations: Sequence[dict[str, object]],
) -> SourceIndex:
    case_text = {case.id: case.narrative for case in cases}
    recall_text = {
        str(row["id"]): str(row.get("summary", ""))
        for row in recalls
        if isinstance(row.get("id"), str)
    }
    investigation_text = {
        str(row["id"]): str(row.get("summary", ""))
        for row in investigations
        if isinstance(row.get("id"), str)
    }
    return SourceIndex(
        cases=case_text,
        recalls=recall_text,
        investigations=investigation_text,
    )


def _ids(citations: Sequence[Citation]) -> tuple[str, ...]:
    return tuple(citation.source_id for citation in citations)


def _recall_clause(recalls: Sequence[dict[str, object]]) -> str:
    ids = [str(row["id"]) for row in recalls if isinstance(row.get("id"), str)]
    if not ids:
        return ""
    return " Linked recalls: " + ", ".join(ids) + "."


def _investigation_clause(investigations: Sequence[dict[str, object]]) -> str:
    ids = [
        str(row["id"])
        for row in investigations
        if isinstance(row.get("id"), str)
    ]
    if not ids:
        return ""
    return " Linked investigations: " + ", ".join(ids) + "."


def _draft(
    *,
    key: tuple[str, str, int, str],
    stats: ClusterStats,
    linked_cases: Sequence[Case],
    recalls: Sequence[dict[str, object]],
    investigations: Sequence[dict[str, object]],
    sequence: int,
    until: date,
) -> IssueDraft:
    make, model, year, group = key
    issue_id = f"I-{until:%Y%m%d}-{sequence:03d}"
    eight_d_id = f"8D-{issue_id}"
    memo_id = f"M-{issue_id}"
    week_start = stats.weekly[-1].week_start if stats.weekly else until
    cited_cases = list(linked_cases[:MAX_CITED_CASES])
    sources = _source_index(cited_cases, recalls, investigations)
    case_citations = _case_citations(cited_cases)
    recall_citations = _event_citations(SourceType.RECALL, recalls)
    investigation_citations = _event_citations(SourceType.INVESTIGATION, investigations)
    citations = checked_citations(
        (*case_citations, *recall_citations, *investigation_citations),
        sources,
    )
    cited_ids = _ids(citations)
    if not cited_ids:
        raise UncitedStatementError("an issue draft needs at least one linked id")

    case_ids = _ids(case_citations)
    joined = ", ".join(case_ids)
    recall_clause = _recall_clause(recalls)
    investigation_clause = _investigation_clause(investigations)
    spike_ratio = round(stats.observed / stats.threshold, 4) if stats.threshold else 0.0

    d2_problem = _ensure_cited(
        f"{stats.observed} {group} reports for {make} {model} {year} in the week "
        f"of {week_start.isoformat()} exceed the Poisson threshold of "
        f"{stats.threshold:g}. Linked cases: {joined}.",
        cited_ids,
    )
    d3_containment = _ensure_cited(
        f"Hold {group} stock for {make} {model} {year} pending inspection and "
        f"re-read the linked cases: {joined}.{recall_clause}{investigation_clause}",
        cited_ids,
    )
    d4_hypotheses = (
        _ensure_cited(
            f"A batch or supplier-process drift in the {group} group explains the "
            f"cluster; inspect the lot history for {joined}.",
            cited_ids,
        ),
        _ensure_cited(
            f"A connector, seal or mounting fault appears under the reported "
            f"conditions; run the targeted test on {joined}.",
            cited_ids,
        ),
        _ensure_cited(
            "Some reports may be duplicates or mis-coded; the linked cases were "
            f"read before opening this issue: {joined}.",
            cited_ids,
        ),
    )
    memo_body = "\n\n".join(
        (
            f"Issue {issue_id}: {make} {model} {year} {group} reports reached "
            f"{stats.observed} in the week of {week_start.isoformat()}, against a "
            f"threshold of {stats.threshold:g} (spike ratio {spike_ratio:g}). "
            f"Linked cases: {joined}.",
            f"Containment: hold the affected stock and inspect it before release. "
            f"The linked recalls and investigations are read with the cases: {joined}."
            f"{recall_clause}{investigation_clause}",
            f"Decision requested: approve the containment and the 8D draft "
            f"{eight_d_id} for {joined}. No case is closed, scrapped or charged "
            "by this desk.",
        )
    )
    for paragraph in memo_body.split("\n\n"):
        _ensure_cited(paragraph, cited_ids)

    issue = Issue(
        id=issue_id,
        title=f"{group} reports cluster for {make} {model} {year}",
        opened_at=until,
        status=IssueStatus.OPEN,
        make=make,
        model=model,
        year=year,
        group=group,
        weekly_counts=stats.weekly,
        observed=stats.observed,
        threshold=stats.threshold,
        spike_ratio=spike_ratio,
        linked_case_ids=tuple(sorted(case.id for case in linked_cases)),
        linked_recall_ids=tuple(
            sorted(str(row["id"]) for row in recalls if isinstance(row.get("id"), str))
        ),
        linked_investigation_ids=tuple(
            sorted(
                str(row["id"])
                for row in investigations
                if isinstance(row.get("id"), str)
            )
        ),
        eight_d_id=eight_d_id,
        memo_id=memo_id,
    )
    created = _at(until, 18, sequence)
    eight_d = EightD(
        id=eight_d_id,
        issue_id=issue_id,
        d1_team=(
            "Quality engineer (placeholder)",
            "Supplier process owner (placeholder)",
            "Fleet data analyst (placeholder)",
        ),
        d2_problem=d2_problem,
        d3_containment=d3_containment,
        d4_root_cause_hypotheses=d4_hypotheses,
        citations=citations,
        created_at=created,
    )
    memo = DecisionMemo(
        id=memo_id,
        issue_id=issue_id,
        title=f"Decision memo: contain the {group} cluster for {make} {model} {year}",
        body=memo_body,
        citations=citations,
        created_at=created,
    )
    return IssueDraft(issue=issue, eight_d=eight_d, memo=memo)


def review_day(
    *,
    cases: Sequence[Case],
    until: date,
    tools: IssueTools,
    existing_issues: Sequence[Issue] = (),
    min_linked_cases: int = MIN_LINKED_CASES,
    lookback_days: int = LOOKBACK_DAYS,
) -> IssueAgentResult:
    """Review every recent vehicle/group key and open issues for standing spikes.

    ``cases`` is every case received so far. A key is rechecked when it has a
    report inside the lookback window; an already-open key is not opened twice.
    """

    window_start = until - timedelta(days=lookback_days)
    recent = [case for case in cases if _received(case) >= window_start]
    keys = sorted(
        {
            (str(case.make), str(case.model),
             int(case.year), str(case.group))
            for case in recent
            if case.group
        }
    )
    open_keys = {
        (issue.make, issue.model, issue.year, issue.group)
        for issue in existing_issues
        if issue.status in (IssueStatus.OPEN, IssueStatus.MONITORING)
    }
    drafts: list[IssueDraft] = []
    for key in keys:
        if key in open_keys:
            continue
        make, model, year, group = key
        stats = tools.cluster_stats(make, model, year, group, until)
        if not stats.spike:
            continue
        linked = [
            case
            for case in cases
            if str(case.make) == make
            and str(case.model) == model
            and int(case.year) == year
            and str(case.group) == group
            and window_start <= _received(case) <= until
        ]
        if len(linked) < min_linked_cases:
            continue
        linked.sort(key=lambda case: (_received(case), str(case.id)))
        recalls = tools.recalls_for(make, model, year, group)
        investigations = tools.investigations_for(make, model, year, group)
        sequence = len(existing_issues) + len(drafts) + 1
        drafts.append(
            _draft(
                key=key,
                stats=stats,
                linked_cases=linked,
                recalls=recalls,
                investigations=investigations,
                sequence=sequence,
                until=until,
            )
        )
    return IssueAgentResult(drafts=tuple(drafts))


def _received(case: Case) -> date:
    return case.received_at
