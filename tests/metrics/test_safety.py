"""Hand-computed fixtures for safety precision and recall."""

from __future__ import annotations

import pytest

from field_quality_agents.metrics import safety_scores


def test_safety_scores_match_hand_computation() -> None:
    # tp=1, fp=1, fn=2, tn=1
    truth = [True, True, False, False, True]
    predicted = [True, False, True, False, False]
    precision, recall = safety_scores(truth, predicted)

    assert precision.value == pytest.approx(0.5)
    assert precision.n == 2  # predicted positives
    assert recall.value == pytest.approx(1 / 3)
    assert recall.n == 3  # actual positives

    # Wilson 95% intervals, checked against the closed form.
    assert precision.ci_low == pytest.approx(0.0945, abs=1e-4)
    assert precision.ci_high == pytest.approx(0.9055, abs=1e-4)
    assert recall.ci_low == pytest.approx(0.0615, abs=1e-4)
    assert recall.ci_high == pytest.approx(0.7923, abs=1e-4)


def test_absent_positives_report_zero_with_zero_denominator() -> None:
    precision, recall = safety_scores([False, False], [False, False])
    assert precision.value == 0.0
    assert precision.n == 0
    assert recall.value == 0.0
    assert recall.n == 0


def test_all_positive_and_all_flagged_is_one() -> None:
    precision, recall = safety_scores([True, True], [True, True])
    assert precision.value == 1.0
    assert recall.value == 1.0
    assert precision.ci_low is not None and precision.ci_high == 1.0


def test_length_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="same length"):
        safety_scores([True], [True, False])
