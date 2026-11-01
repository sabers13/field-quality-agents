"""The linear pipeline's fixed sequence and its refusal to read the truth."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from field_quality_agents.baseline import KeywordRules, load_keywords, run_linear
from field_quality_agents.baseline.pipeline import baseline_runs
from field_quality_agents.contracts import Case

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def rules() -> KeywordRules:
    return load_keywords(REPO_ROOT / "config" / "keywords.toml")


def _case(
    case_id: str,
    component: str,
    narrative: str,
    *,
    group: str | None = None,
    safety_relevant: bool = False,
) -> Case:
    return Case(
        id=case_id,
        received_at=date(2025, 3, 4),
        make="HONDA",
        model="ACCORD",
        year=2020,
        component=component,
        narrative=narrative,
        group=group,
        safety_relevant=safety_relevant,
    )


def test_standard_test_always_closes_no_trouble_found(rules: KeywordRules) -> None:
    case = _case("C1", "ELECTRICAL SYSTEM:12V/24V/48V BATTERY", "The battery dies overnight.")
    decision = run_linear([case], rules)[0]

    assert decision.group == "power_and_wiring"
    assert decision.safety_relevant is False
    assert decision.route == "standard_test"
    assert decision.closed_no_trouble_found is True


def test_safety_routes_to_priority_and_does_not_close(rules: KeywordRules) -> None:
    case = _case("C2", "ELECTRICAL SYSTEM:WIRING", "The harness caught fire while driving.")
    decision = run_linear([case], rules)[0]

    assert decision.safety_relevant is True
    assert decision.route == "priority"
    assert decision.closed_no_trouble_found is False
    assert "caught fire" in decision.keywords


def test_unclear_report_still_takes_the_standard_test(rules: KeywordRules) -> None:
    case = _case("C3", "ENGINE", "The engine misfires when cold.")
    decision = run_linear([case], rules)[0]

    assert decision.group == "unclear"
    assert decision.route == "standard_test"
    assert decision.closed_no_trouble_found is True


def test_pipeline_ignores_nhtsa_truth_fields(rules: KeywordRules) -> None:
    # Truth says restraints and safety; the report text says neither. The
    # baseline must follow the text, or every metric would be leaked.
    case = _case(
        "C4",
        "ENGINE",
        "The engine misfires when cold.",
        group="restraints",
        safety_relevant=True,
    )
    decision = run_linear([case], rules)[0]

    assert decision.group == "unclear"
    assert decision.safety_relevant is False
    assert decision.route == "standard_test"


def test_keywords_record_sort_and_safety_hits(rules: KeywordRules) -> None:
    case = _case("C5", "ELECTRICAL SYSTEM:WIRING", "Wiring smoke and a battery fire.")
    decision = run_linear([case], rules)[0]

    assert "wiring" in decision.keywords
    assert "battery" in decision.keywords
    assert "battery fire" in decision.keywords


def test_baseline_runs_produce_one_human_touch_and_four_steps(rules: KeywordRules) -> None:
    case = _case("C6", "EXTERIOR LIGHTING", "The headlights flicker.")
    decisions = run_linear([case], rules)
    runs = baseline_runs([case], decisions)

    assert len(runs) == 1
    assert runs[0].steps == 4
    assert sum(1 for step in runs[0].trace if step.agent == "human") == 1
    assert [step.step for step in runs[0].trace] == [1, 2, 3, 4]
    assert runs[0].trace[-1].action == "close_no_trouble_found"
