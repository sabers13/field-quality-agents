"""Fleet cluster statistics and the PLAN §4 spike rule."""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any

from field_quality_agents.contracts import WeekCount
from field_quality_agents.tools.db import Toolbox
from field_quality_agents.tools.models import ClusterStats

__all__ = ["cluster_stats", "poisson_threshold", "poisson_upper_tail"]

_BASELINE_WEEKS = 26
_ALPHA = 0.001
_MINIMUM_THRESHOLD = 3
_MEAN_FLOOR = 0.5


def _poisson_cdf(k: int, mean: float) -> float:
    """P(X <= k) for X ~ Poisson(mean), computed iteratively."""

    if k < 0:
        return 0.0
    term = math.exp(-mean)
    total = term
    for index in range(1, k + 1):
        term *= mean / index
        total += term
    return min(total, 1.0)


def poisson_upper_tail(k: int, mean: float) -> float:
    """P(X >= k) for X ~ Poisson(mean)."""

    if k <= 0:
        return 1.0
    return max(0.0, 1.0 - _poisson_cdf(k - 1, mean))


def poisson_threshold(
    mean: float,
    *,
    alpha: float = _ALPHA,
    minimum: int = _MINIMUM_THRESHOLD,
) -> int:
    """Smallest count with a Poisson tail at or below ``alpha``.

    The trailing mean is floored at 0.5 so a quiet cluster still needs a
    meaningful count. ``minimum`` keeps the PLAN §4 "count >= 3" floor.
    """

    rate = max(mean, _MEAN_FLOOR)
    count = max(minimum, 1)
    while count < 10_000:
        if poisson_upper_tail(count, rate) <= alpha:
            return count
        count += 1
    return count


def _week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def cluster_stats(
    toolbox: Toolbox,
    make: str,
    model: str,
    year: int,
    group: str,
    until_date: date,
) -> ClusterStats:
    """Weekly series and spike state for one vehicle key.

    The series has 27 points: the 26-week trailing baseline followed by the
    week containing ``until_date``. ``trailing_mean`` is the mean of the 26
    baseline weeks. ``threshold`` is the smallest Poisson count whose upper
    tail is at most 0.1%, with the mean floored at 0.5 and a floor of 3.
    """

    current_week = _week_start(until_date)
    baseline_start = current_week - timedelta(weeks=_BASELINE_WEEKS)
    rows: list[tuple[Any, ...]] = toolbox.connection.execute(
        """
        SELECT week_start, "count"
        FROM fleet_weekly
        WHERE upper(make) = upper(?)
          AND upper(model) = upper(?)
          AND year = ?
          AND "group" = ?
          AND week_start >= ?
          AND week_start <= ?
        ORDER BY week_start
        """,
        [make, model, year, group, baseline_start, current_week],
    ).fetchall()
    counts = {row[0]: int(row[1]) for row in rows}
    weeks = [baseline_start + timedelta(weeks=index) for index in range(_BASELINE_WEEKS + 1)]
    weekly = tuple(WeekCount(week_start=week, count=counts.get(week, 0)) for week in weeks)
    baseline = weekly[:_BASELINE_WEEKS]
    trailing_mean = sum(week.count for week in baseline) / _BASELINE_WEEKS
    observed = weekly[-1].count
    threshold = poisson_threshold(trailing_mean)
    return ClusterStats(
        make=make,
        model=model,
        year=year,
        group=group,
        until_date=until_date,
        weekly=weekly,
        trailing_mean=round(trailing_mean, 4),
        threshold=float(threshold),
        observed=observed,
        spike=observed >= threshold,
    )
