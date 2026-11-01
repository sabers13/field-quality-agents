"""Shared estimate helpers: rounding, Wilson intervals and bootstrap draws.

Every public metric in :mod:`field_quality_agents.metrics` returns
``MetricEstimate`` objects from ``contracts.py``. The helpers here keep the
arithmetic in one place so both pipelines get identical intervals.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from field_quality_agents.contracts import MetricEstimate

__all__ = [
    "DEFAULT_SEED",
    "estimate",
    "mean",
    "percentile",
    "wilson_interval",
]

#: PLAN §5's replay-set seed; reused as the default bootstrap seed.
DEFAULT_SEED = 20261031

#: Two-sided 95% normal quantile, used by the Wilson interval.
_Z95 = 1.959963984540054


def _round(value: float) -> float:
    return round(value, 6)


def estimate(
    value: float,
    *,
    ci_low: float | None = None,
    ci_high: float | None = None,
    n: int = 0,
) -> MetricEstimate:
    """Build a rounded ``MetricEstimate``."""

    return MetricEstimate(
        value=_round(value),
        ci_low=None if ci_low is None else _round(ci_low),
        ci_high=None if ci_high is None else _round(ci_high),
        n=n,
    )


def wilson_interval(successes: int, n: int, *, z: float = _Z95) -> tuple[float, float]:
    """Wilson score interval for a binomial share.

    With no observations the interval is the whole unit range, reported as
    ``(0.0, 0.0)`` because there is no share to bound.
    """

    if n <= 0:
        return 0.0, 0.0
    if successes < 0 or successes > n:
        raise ValueError("successes must be between 0 and n")
    p = successes / n
    denominator = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denominator
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def percentile(values: Sequence[float], q: float) -> float:
    """Linear-interpolated percentile for ``0 <= q <= 1``."""

    if not values:
        return 0.0
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be between 0 and 1")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
