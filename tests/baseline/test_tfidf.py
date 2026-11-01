"""The TF-IDF reference on a tiny, clearly separable fixture."""

from __future__ import annotations

from datetime import date

import pytest

from field_quality_agents.baseline import run_tfidf_logreg
from field_quality_agents.contracts import Case


def _case(case_id: str, narrative: str, group: str) -> Case:
    return Case(
        id=case_id,
        received_at=date(2024, 1, 1),
        make="HONDA",
        model="ACCORD",
        year=2020,
        component="ELECTRICAL SYSTEM",
        narrative=narrative,
        group=group,
    )


TRAIN = [
    _case("T1", "forward collision braking engaged for no reason", "adas"),
    _case("T2", "forward collision warning and automatic braking problem", "adas"),
    _case("T3", "headlight bulb keeps burning out at night", "lighting"),
    _case("T4", "headlight and tail light bulb failure", "lighting"),
    _case("T5", "the airbag warning lamp stays on", "restraints"),
    _case("T6", "airbag and seat belt restraint warning", "restraints"),
]

TEST = [
    _case("E1", "automatic braking and forward collision fault", "adas"),
    _case("E2", "another headlight bulb failure", "lighting"),
    _case("E3", "airbag warning lamp on the dash", "restraints"),
]


def test_tfidf_reference_separates_the_fixture() -> None:
    predictions = run_tfidf_logreg(TRAIN, TEST)
    assert predictions == ["adas", "lighting", "restraints"]


def test_tfidf_reference_is_deterministic() -> None:
    assert run_tfidf_logreg(TRAIN, TEST) == run_tfidf_logreg(TRAIN, TEST)


def test_empty_training_set_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        run_tfidf_logreg([], TEST)


def test_single_class_training_set_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least two"):
        run_tfidf_logreg([TRAIN[0], TRAIN[1]], TEST)
