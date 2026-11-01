"""Choose the before/after showcase examples by fixed, auditable rules.

The dashboard's comparison page shows a handful of cases. They are not picked
by hand: each one is the first case (or the longest trace) that satisfies one
rule below, read from the run's own committed files.

The three required rules are:

1. **Fleet signal.** The earliest opened issue that preceded a matching NHTSA
   recall or investigation by at most 365 days. This is exactly PLAN §7's
   "early issue" rule, so the example and the issue-precision metric cannot
   disagree. In this snapshot no issue preceded an investigation; two issues
   preceded a recall, and the earliest of those is chosen.
2. **Longest trace with a targeted test.** The case whose agent trace is the
   longest among cases that ended with a targeted load test proposal.
3. **Missed clue.** The first case (in received-date order) that the linear
   pipeline closed as no trouble found while the agent verified at least one
   quotation and proposed an evidence-backed test.

A fourth, reverse example shows a case where the linear pipeline was right,
so the page never reads as one-sided.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from field_quality_agents.api.models import ComparisonExample

__all__ = ["WINDOW_DAYS", "choose_examples"]

#: PLAN §7: a fleet event counts when it follows within one year.
WINDOW_DAYS = 365


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _day(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _linked_events(
    issue: dict[str, Any],
    evidence: dict[str, Any],
) -> list[tuple[date, str, str]]:
    """Dates of the issue's linked recalls and investigations, from evidence."""

    recall_ids = set(issue.get("linked_recall_ids") or [])
    investigation_ids = set(issue.get("linked_investigation_ids") or [])
    found: dict[str, tuple[date, str, str]] = {}
    for case_id in issue.get("linked_case_ids") or []:
        case_evidence = evidence.get(case_id) or {}
        for kind, ids in (("Recall", recall_ids), ("Investigation", investigation_ids)):
            for row in case_evidence.get("recalls" if kind == "Recall" else "investigations") or []:
                source_id = row.get("id")
                opened = _day(row.get("open_date"))
                if source_id in ids and opened is not None and source_id not in found:
                    found[source_id] = (opened, kind, source_id)
    return list(found.values())


def _fleet_example(
    issues: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> ComparisonExample | None:
    ordered = sorted(issues, key=lambda issue: (str(issue.get("opened_at")), str(issue.get("id"))))
    early: list[tuple[date, str, dict[str, Any], tuple[date, str, str]]] = []
    for issue in ordered:
        opened = _day(issue.get("opened_at"))
        if opened is None:
            continue
        following = [
            event
            for event in _linked_events(issue, evidence)
            if opened <= event[0] <= opened + timedelta(days=WINDOW_DAYS)
        ]
        if following:
            early.append((opened, str(issue.get("id")), issue, min(following)))
    if not early:
        if not ordered:
            return None
        first = ordered[0]
        opened_text = str(first.get("opened_at"))[:10]
        return ComparisonExample(
            case_id=str((first.get("linked_case_ids") or [""])[0]),
            before="The linear pipeline has no fleet-level issue step.",
            after=f"The issue agent opened {first.get('id')} on {opened_text}.",
            note=(
                "The earliest issue in the run; no matching recall or "
                "investigation followed it yet."
            ),
        )

    opened, _, issue, (event_date, kind, source_id) = early[0]
    lead = (event_date - opened).days
    return ComparisonExample(
        case_id=str((issue.get("linked_case_ids") or [""])[0]),
        before="The linear pipeline has no fleet-level issue step.",
        after=(
            f"The issue agent opened {issue.get('id')} on {opened.isoformat()}, "
            f"{lead} days before NHTSA published {kind.lower()} {source_id} "
            f"({event_date.isoformat()})."
        ),
        note="The earliest issue that preceded a matching recall or investigation.",
    )


def _targeted_example(
    traces: dict[str, Any],
    proposals: dict[str, Any],
) -> ComparisonExample | None:
    targeted = [
        case_id
        for case_id, proposal in proposals.items()
        if (proposal or {}).get("kind") == "targeted_load_test"
    ]
    if not targeted:
        return None
    longest = max(targeted, key=lambda case_id: (len(traces.get(case_id) or []), case_id))
    steps = len(traces.get(longest) or [])
    return ComparisonExample(
        case_id=longest,
        before="Standard test; the linear simulation always passes it.",
        after=f"Targeted load test requested after {steps} trace steps.",
        note="The longest agent trace that ended in a targeted test.",
    )


def _verified_evidence(proposal: dict[str, Any] | None) -> bool:
    if not proposal:
        return False
    return any(
        bool(citation.get("verified")) and bool(citation.get("quote"))
        for citation in proposal.get("evidence") or []
    )


def _missed_clue_example(
    cases: list[dict[str, Any]],
    proposals: dict[str, Any],
    baseline: dict[str, bool],
) -> ComparisonExample | None:
    ordered = sorted(cases, key=lambda case: (str(case.get("received_at")), str(case.get("id"))))
    for case in ordered:
        case_id = str(case.get("id"))
        if not baseline.get(case_id):
            continue
        if not _verified_evidence(proposals.get(case_id)):
            continue
        return ComparisonExample(
            case_id=case_id,
            before="Closed as no trouble found.",
            after="The agent verified a quotation and proposed an evidence-backed test.",
            note="Where the linear pipeline missed what the agent found.",
        )
    return None


def _reverse_example(
    cases: list[dict[str, Any]],
    proposals: dict[str, Any],
    baseline: dict[str, bool],
) -> ComparisonExample | None:
    ordered = sorted(cases, key=lambda case: (str(case.get("received_at")), str(case.get("id"))))
    for case in ordered:
        case_id = str(case.get("id"))
        if not baseline.get(case_id):
            continue
        if _verified_evidence(proposals.get(case_id)):
            continue
        return ComparisonExample(
            case_id=case_id,
            before="Closed as no trouble found with the keyword rules.",
            after="The agent also found no verified evidence.",
            note="Reverse: where the linear pipeline was right too.",
        )
    return None


def choose_examples(run_dir: str | Path, baseline_dir: str | Path) -> list[ComparisonExample]:
    """Return the fixed showcase examples, or an empty list without records."""

    run = Path(run_dir)
    if not run.is_dir():
        return []
    issues = _read(run / "issues.json", [])
    evidence = _read(run / "evidence.json", {})
    traces = _read(run / "traces.json", {})
    proposals = _read(run / "proposals.json", {})
    cases = _read(run / "cases.json", [])
    decisions = _read(Path(baseline_dir) / "decisions.json", [])
    baseline = {
        str(row.get("case_id")): bool(row.get("closed_no_trouble_found"))
        for row in decisions
        if isinstance(row, dict)
    }

    examples = [
        _fleet_example(issues, evidence),
        _targeted_example(traces, proposals),
        _missed_clue_example(cases, proposals, baseline),
        _reverse_example(cases, proposals, baseline),
    ]
    return [example for example in examples if example is not None]
