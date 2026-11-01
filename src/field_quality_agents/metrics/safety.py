"""Safety metrics: precision and recall against the crash/fire/injury/death flag."""

from __future__ import annotations

from collections.abc import Sequence

from field_quality_agents.contracts import MetricEstimate
from field_quality_agents.metrics.estimates import estimate, wilson_interval

__all__ = ["safety_scores"]


def _counts(
    y_true: Sequence[bool],
    y_pred: Sequence[bool],
) -> tuple[int, int, int, int]:
    true_positive = 0
    false_positive = 0
    false_negative = 0
    true_negative = 0
    for truth, predicted in zip(y_true, y_pred, strict=True):
        if truth and predicted:
            true_positive += 1
        elif predicted:
            false_positive += 1
        elif truth:
            false_negative += 1
        else:
            true_negative += 1
    return true_positive, false_positive, false_negative, true_negative


def safety_scores(
    y_true: Sequence[bool],
    y_pred: Sequence[bool],
) -> tuple[MetricEstimate, MetricEstimate]:
    """Return ``(precision, recall)`` with Wilson intervals.

    ``n`` on each estimate is its own denominator: predicted positives for
    precision, actual positives for recall.
    """

    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    true_positive, false_positive, false_negative, _ = _counts(y_true, y_pred)

    predicted_positive = true_positive + false_positive
    precision_low, precision_high = wilson_interval(true_positive, predicted_positive)
    precision = estimate(
        true_positive / predicted_positive if predicted_positive else 0.0,
        ci_low=precision_low,
        ci_high=precision_high,
        n=predicted_positive,
    )

    actual_positive = true_positive + false_negative
    recall_low, recall_high = wilson_interval(true_positive, actual_positive)
    recall = estimate(
        true_positive / actual_positive if actual_positive else 0.0,
        ci_low=recall_low,
        ci_high=recall_high,
        n=actual_positive,
    )

    return precision, recall
