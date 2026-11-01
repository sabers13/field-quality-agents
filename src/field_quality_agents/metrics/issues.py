"""Issue-detection metrics against NHTSA investigation and recall events.

An opened issue is *early* when a matching event (same make, model, model year
and component group) follows within 365 days. PLAN §7 asks for three things:
the share that are early, the median lead time, and the same share for random
weeks of the same series, which is the headline base rate.
"""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from field_quality_agents.contracts import Case, Issue
from field_quality_agents.metrics.estimates import DEFAULT_SEED, mean

__all__ = ["Event", "issue_detection"]

SeriesKey = tuple[str, str, int, str]


@dataclass(frozen=True)
class Event:
    """One ground-truth recall or investigation row."""

    make: str
    model: str
    year: int
    group: str
    event_type: Literal["recall", "investigation"]
    event_date: date
    source_id: str

    @property
    def key(self) -> SeriesKey:
        return (self.make, self.model, self.year, self.group)


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _first_following(
    events: Sequence[Event],
    start: date,
    window_days: int,
) -> Event | None:
    end = start + timedelta(days=window_days)
    candidates = [event for event in events if start <= event.event_date <= end]
    if not candidates:
        return None
    return min(candidates, key=lambda event: (event.event_date, event.source_id))


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def issue_detection(
    issues: Sequence[Issue],
    truth: Sequence[Event],
    *,
    cases: Sequence[Case],
    rng: random.Random | None = None,
    window_days: int = 365,
) -> dict[str, float]:
    """Return issue precision, median lead days and the random-week base rate.

    Random weeks are drawn from the study window covered by ``cases`` and are
    scored with the same event rule for the issue's own series. The seeded
    ``rng`` keeps the base rate reproducible.
    """

    events_by_key: dict[SeriesKey, list[Event]] = defaultdict(list)
    for event_row in truth:
        events_by_key[event_row.key].append(event_row)

    early = 0
    lead_days: list[float] = []
    for issue in issues:
        key: SeriesKey = (issue.make, issue.model, issue.year, issue.group)
        following = _first_following(events_by_key.get(key, []), issue.opened_at, window_days)
        if following is not None:
            early += 1
            lead_days.append(float((following.event_date - issue.opened_at).days))

    opened = len(issues)
    precision = early / opened if opened else 0.0

    case_dates = [case.received_at for case in cases]
    weeks: list[date] = []
    if case_dates:
        cursor = _monday(min(case_dates))
        last = _monday(max(case_dates))
        while cursor <= last:
            weeks.append(cursor)
            cursor += timedelta(days=7)

    random_source = rng if rng is not None else random.Random(DEFAULT_SEED)
    random_week_hits: list[float] = []
    for issue in issues:
        if not weeks:
            random_week_hits.append(0.0)
            continue
        week = weeks[random_source.randrange(len(weeks))]
        key = (issue.make, issue.model, issue.year, issue.group)
        following = _first_following(events_by_key.get(key, []), week, window_days)
        random_week_hits.append(1.0 if following is not None else 0.0)

    return {
        "issues": float(opened),
        "early_issues": float(early),
        "issue_precision": precision,
        "issue_median_lead_days": _median(lead_days),
        "issue_base_rate": mean(random_week_hits),
    }
