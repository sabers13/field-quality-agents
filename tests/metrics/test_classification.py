"""Hand-computed fixtures for the component-group metrics."""

from __future__ import annotations

import random

import pytest

from field_quality_agents.metrics import group_coverage, macro_f1


def test_macro_f1_matches_hand_computation() -> None:
    y_true = ["a", "a", "b", "b"]
    y_pred = ["a", "b", "b", "b"]
    # a: tp=1 fp=0 fn=1 -> 2/(2+0+1) = 2/3
    # b: tp=2 fp=1 fn=0 -> 4/(4+1+0) = 4/5
    result = macro_f1(y_true, y_pred, rng=random.Random(7))
    assert result.value == pytest.approx((2 / 3 + 4 / 5) / 2, abs=1e-6)
    assert result.n == 4
    assert result.ci_low is not None and result.ci_high is not None
    assert result.ci_low <= result.value <= result.ci_high


def test_macro_f1_perfect_prediction_has_zero_width_interval() -> None:
    result = macro_f1(["a", "b", "a"], ["a", "b", "a"], rng=random.Random(7))
    assert result.value == 1.0
    assert result.ci_low == 1.0
    assert result.ci_high == 1.0


def test_unclear_prediction_counts_as_wrong() -> None:
    result = macro_f1(["a", "b"], ["unclear", "b"], rng=random.Random(7))
    # a never matched, b perfect -> (0 + 1) / 2
    assert result.value == 0.5


def test_macro_f1_is_reproducible_for_a_seed() -> None:
    truth = ["a", "a", "b", "b", "c", "c"]
    predicted = ["a", "b", "b", "c", "c", "c"]
    first = macro_f1(truth, predicted, rng=random.Random(99))
    second = macro_f1(truth, predicted, rng=random.Random(99))
    assert first == second


def test_macro_f1_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError, match="same length"):
        macro_f1(["a"], ["a", "b"])


def test_empty_metrics_are_zero_with_no_observations() -> None:
    result = macro_f1([], [])
    assert result.value == 0.0
    assert result.n == 0
    assert group_coverage([]).n == 0


def test_group_coverage_is_the_share_of_concrete_predictions() -> None:
    result = group_coverage(["adas", "unclear", "lighting", "unclear"])
    assert result.value == 0.5
    assert result.n == 4
    assert result.ci_low is not None and result.ci_high is not None
