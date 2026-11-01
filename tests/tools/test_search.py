from __future__ import annotations

from field_quality_agents.tools import CaseFilters, similar_cases


def test_similar_cases_is_deterministic_and_sorted() -> None:
    filters = CaseFilters(make="FORD", model="F-150", year=2021, group="body_controls")
    first = similar_cases("intermittent wiper", filters, 10)
    second = similar_cases("intermittent wiper", filters, 10)
    assert first == second
    assert [case.id for case in first[:2]] == ["c17", "c02"]
    assert all(case.score == round(case.score, 4) for case in first)
    assert first == sorted(first, key=lambda case: (-case.score, case.id))


def test_similar_cases_scores_are_four_decimal_places() -> None:
    cases = similar_cases("wiper motor", CaseFilters(make="FORD", model="F-150", year=2021))
    assert cases
    for case in cases:
        assert case.score == round(case.score, 4)


def test_equal_scores_tie_break_by_id() -> None:
    filters = CaseFilters(make="TESLA", model="MODEL 3", year=2022)
    cases = similar_cases("charging port overheats during fast charging", filters, 10)
    ids = [case.id for case in cases]
    assert ids.index("c09") < ids.index("c10")
    by_id = {case.id: case for case in cases}
    assert by_id["c09"].score == by_id["c10"].score


def test_filters_are_applied() -> None:
    filters = CaseFilters(make="TESLA", model="MODEL 3", year=2022)
    ids = [case.id for case in similar_cases("charging port overheats", filters, 20)]
    assert "c11" not in ids  # different model
    assert "c12" not in ids  # different make
    assert "c19" not in ids  # different group
    assert "c06" in ids


def test_filter_matching_is_case_insensitive() -> None:
    lower = similar_cases("wiper", CaseFilters(make="ford", model="f-150", year=2021), 5)
    upper = similar_cases("wiper", CaseFilters(make="FORD", model="F-150", year=2021), 5)
    assert [case.id for case in lower] == [case.id for case in upper]


def test_safety_filter() -> None:
    unsafe = similar_cases("charging", CaseFilters(safety_relevant=False), 20)
    safe = similar_cases("charging", CaseFilters(safety_relevant=True), 20)
    assert "c18" in {case.id for case in unsafe}
    assert "c18" not in {case.id for case in safe}


def test_k_limits_results() -> None:
    filters = CaseFilters(make="FORD", model="F-150", year=2021, group="body_controls")
    assert len(similar_cases("wiper", filters, 2)) == 2
    assert similar_cases("wiper", filters, 0) == []


def test_empty_or_stopword_query_returns_nothing() -> None:
    assert similar_cases("", None, 10) == []
    assert similar_cases("the and of", None, 10) == []


def test_long_narrative_is_truncated() -> None:
    cases = similar_cases("grinds", CaseFilters(make="FORD", model="F-150", year=2021), 5)
    assert [case.id for case in cases] == ["c20"]
    excerpt = cases[0].excerpt
    assert excerpt.endswith("...")
    assert len(excerpt) <= 283
    assert "\n" not in excerpt
