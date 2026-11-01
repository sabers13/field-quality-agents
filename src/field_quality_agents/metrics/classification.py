"""Component-group metrics: macro-F1 with a bootstrap CI, and coverage.

Macro-F1 is averaged over the labels present in the truth set. A prediction
outside that set — including the baseline's ``unclear`` — can never be a true
positive, so it counts as wrong for the label it should have matched. That is
the PLAN §7 rule; ``unclear`` is not given a class average of its own.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from field_quality_agents.contracts import MetricEstimate
from field_quality_agents.metrics.estimates import (
    DEFAULT_SEED,
    estimate,
    percentile,
    wilson_interval,
)

__all__ = ["group_coverage", "macro_f1"]


def _f1_for_label(y_true: Sequence[str], y_pred: Sequence[str], label: str) -> float:
    true_positive = 0
    false_positive = 0
    false_negative = 0
    for truth, predicted in zip(y_true, y_pred, strict=True):
        if truth == label and predicted == label:
            true_positive += 1
        elif predicted == label:
            false_positive += 1
        elif truth == label:
            false_negative += 1
    denominator = 2 * true_positive + false_positive + false_negative
    if denominator == 0:
        return 0.0
    return 2 * true_positive / denominator


def _macro_f1_value(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str],
) -> float:
    if not labels:
        return 0.0
    return sum(_f1_for_label(y_true, y_pred, label) for label in labels) / len(labels)


def macro_f1(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    *,
    rng: random.Random | None = None,
    n_resamples: int = 2_000,
) -> MetricEstimate:
    """Macro-F1 against NHTSA coding, with a percentile bootstrap CI.

    ``rng`` is a seeded ``random.Random`` owned by the caller, so the same
    inputs always produce the same interval. With no seed, PLAN §5's seed is
    used.
    """

    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    if not y_true:
        return estimate(0.0, n=0)
    labels = tuple(sorted(set(y_true)))
    value = _macro_f1_value(y_true, y_pred, labels)

    random_source = rng if rng is not None else random.Random(DEFAULT_SEED)
    size = len(y_true)
    draws: list[float] = []
    for _ in range(n_resamples):
        indices = [random_source.randrange(size) for _ in range(size)]
        sampled_truth = [y_true[index] for index in indices]
        sampled_prediction = [y_pred[index] for index in indices]
        sampled_labels = tuple(sorted(set(sampled_truth)))
        draws.append(_macro_f1_value(sampled_truth, sampled_prediction, sampled_labels))

    return estimate(
        value,
        ci_low=percentile(draws, 0.025),
        ci_high=percentile(draws, 0.975),
        n=size,
    )


def group_coverage(y_pred: Sequence[str], *, unclear: str = "unclear") -> MetricEstimate:
    """Share of reports that received a concrete group rather than ``unclear``."""

    n = len(y_pred)
    successes = sum(1 for label in y_pred if label != unclear)
    low, high = wilson_interval(successes, n)
    return estimate(successes / n if n else 0.0, ci_low=low, ci_high=high, n=n)
