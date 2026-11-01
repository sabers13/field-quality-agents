"""Hand-computed fixtures for issue detection and the random-week base rate."""

from __future__ import annotations

import random
from datetime import date, timedelta

from field_quality_agents.contracts import Case, Issue
from field_quality_agents.metrics import Event, issue_detection


def _case(received: date, *, year: int = 2020) -> Case:
    return Case(
        id="C1",
        received_at=received,
        make="HONDA",
        model="ACCORD",
        year=year,
        component="EXTERIOR LIGHTING",
        narrative="The headlights fail intermittently while driving at night.",
        group="lighting",
    )


def _issue(issue_id: str, opened: date, *, year: int = 2020) -> Issue:
    return Issue(
        id=issue_id,
        title="Lighting cluster",
        opened_at=opened,
        make="HONDA",
        model="ACCORD",
        year=year,
        group="lighting",
    )


def test_issue_detection_matches_hand_computation() -> None:
    cases = [_case(date(2025, 1, 6))]
    issues = [
        _issue("I1", date(2025, 3, 1)),
        # A different model year has no matching event in this fixture.
        _issue("I2", date(2025, 3, 1), year=2022),
    ]
    truth = [
        Event(
            make="HONDA",
            model="ACCORD",
            year=2020,
            group="lighting",
            event_type="recall",
            event_date=date(2025, 5, 1),
            source_id="R1",
        ),
        # Same make/model/group but another model year: must not count.
        Event(
            make="HONDA",
            model="ACCORD",
            year=2021,
            group="lighting",
            event_type="investigation",
            event_date=date(2025, 5, 1),
            source_id="I9",
        ),
    ]

    result = issue_detection(issues, truth, cases=cases, rng=random.Random(4))

    assert result["issues"] == 2
    assert result["early_issues"] == 1
    assert result["issue_precision"] == 0.5
    assert result["issue_median_lead_days"] == 61
    # The only study week is 2025-01-06: the first issue sees the event within
    # 365 days, the second does not.
    assert result["issue_base_rate"] == 0.5


def test_event_before_the_issue_does_not_count() -> None:
    cases = [_case(date(2025, 1, 6))]
    issues = [_issue("I1", date(2025, 6, 1))]
    truth = [
        Event(
            make="HONDA",
            model="ACCORD",
            year=2020,
            group="lighting",
            event_type="recall",
            event_date=date(2025, 5, 31),
            source_id="R1",
        )
    ]
    result = issue_detection(issues, truth, cases=cases, rng=random.Random(4))
    assert result["issue_precision"] == 0.0
    assert result["issue_median_lead_days"] == 0.0


def test_event_outside_the_365_day_window_does_not_count() -> None:
    cases = [_case(date(2025, 1, 6))]
    issues = [_issue("I1", date(2025, 3, 1))]
    truth = [
        Event(
            make="HONDA",
            model="ACCORD",
            year=2020,
            group="lighting",
            event_type="recall",
            event_date=date(2026, 3, 2),
            source_id="R1",
        )
    ]
    result = issue_detection(issues, truth, cases=cases, rng=random.Random(4))
    assert result["issue_precision"] == 0.0


def test_no_issues_reports_zeros() -> None:
    result = issue_detection([], [], cases=[_case(date(2025, 1, 6))])
    assert result["issues"] == 0.0
    assert result["issue_precision"] == 0.0
    assert result["issue_base_rate"] == 0.0


def test_base_rate_is_reproducible_for_a_seed() -> None:
    cases = [_case(date(2025, 1, 6) + timedelta(days=7 * i)) for i in range(10)]
    issues = [_issue("I1", date(2025, 3, 1)), _issue("I2", date(2025, 4, 1))]
    truth = [
        Event(
            make="HONDA",
            model="ACCORD",
            year=2020,
            group="lighting",
            event_type="recall",
            event_date=date(2025, 6, 1),
            source_id="R1",
        )
    ]
    first = issue_detection(issues, truth, cases=cases, rng=random.Random(11))
    second = issue_detection(issues, truth, cases=cases, rng=random.Random(11))
    assert first == second
