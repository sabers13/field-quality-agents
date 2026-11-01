from __future__ import annotations

from datetime import date, timedelta

from field_quality_agents.tools import cluster_stats
from field_quality_agents.tools.cluster import poisson_threshold, poisson_upper_tail


def test_cluster_stats_zero_fills_the_weekly_series() -> None:
    stats = cluster_stats("HYUNDAI", "IONIQ 5", 2023, "ev_propulsion", date(2025, 7, 7))
    assert len(stats.weekly) == 27
    assert all(week.count == 0 for week in stats.weekly)
    assert stats.weekly[0].week_start == date(2025, 1, 6)
    assert stats.weekly[-1].week_start == date(2025, 7, 7)
    assert stats.trailing_mean == 0.0
    assert stats.observed == 0
    assert stats.spike is False


def test_weekly_points_are_consecutive_weeks() -> None:
    stats = cluster_stats("FORD", "F-150", 2021, "body_controls", date(2025, 7, 7))
    starts = [week.week_start for week in stats.weekly]
    assert starts == [starts[0] + timedelta(weeks=index) for index in range(27)]


def test_spike_uses_trailing_mean_and_poisson_threshold() -> None:
    stats = cluster_stats("FORD", "F-150", 2021, "body_controls", date(2025, 7, 7))
    assert stats.trailing_mean == 0.5
    assert stats.threshold == 5.0
    assert stats.observed == 5
    assert stats.spike is True


def test_observed_below_threshold_is_not_a_spike() -> None:
    quiet = cluster_stats("FORD", "F-150", 2022, "body_controls", date(2025, 7, 7))
    assert quiet.observed == 2
    assert quiet.threshold == 5.0
    assert quiet.spike is False

    four = cluster_stats("FORD", "F-150", 2021, "electrical_general", date(2025, 7, 7))
    assert four.observed == 4
    assert four.spike is False


def test_mean_one_needs_more_than_three_cases() -> None:
    stats = cluster_stats("TESLA", "MODEL 3", 2022, "ev_propulsion", date(2025, 7, 7))
    assert stats.trailing_mean == 1.0
    assert stats.threshold == 6.0
    assert stats.observed == 3
    assert stats.spike is False


def test_until_date_midweek_uses_the_containing_week() -> None:
    monday = cluster_stats("FORD", "F-150", 2021, "body_controls", date(2025, 7, 7))
    wednesday = cluster_stats("FORD", "F-150", 2021, "body_controls", date(2025, 7, 9))
    assert wednesday.weekly[-1].week_start == date(2025, 7, 7)
    assert wednesday.observed == monday.observed
    assert wednesday.spike == monday.spike


def test_until_date_before_the_series_is_all_zeroes() -> None:
    stats = cluster_stats("FORD", "F-150", 2021, "body_controls", date(2024, 1, 1))
    assert stats.observed == 0
    assert stats.trailing_mean == 0.0
    assert stats.spike is False


def test_poisson_threshold_has_a_floor() -> None:
    assert poisson_threshold(0.0) == 5
    assert poisson_threshold(0.5) == 5
    assert poisson_threshold(1.0) == 6
    assert poisson_threshold(2.0) >= 6
    assert poisson_upper_tail(4, 0.5) > 0.001
    assert poisson_upper_tail(5, 0.5) <= 0.001


def test_poisson_threshold_is_monotonic() -> None:
    thresholds = [poisson_threshold(mean / 10) for mean in range(0, 101)]
    assert thresholds == sorted(thresholds)
    assert all(threshold >= 3 for threshold in thresholds)
