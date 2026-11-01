"""The run-level metrics: quote counting and the evaluation-label retraction."""

from __future__ import annotations

from datetime import UTC, date, datetime

from field_quality_agents.agents.state import CaseRun
from field_quality_agents.contracts import (
    Case,
    Clue,
    ClueKind,
    Extraction,
    TraceStep,
)
from field_quality_agents.metrics import SourceIndex
from field_quality_agents.run.metrics import compute_metrics

CREATED = datetime(2025, 1, 2, 7, 0, tzinfo=UTC)
NARRATIVE = "The display goes blank when the cabin is cold and returns when warm."


def _case(**overrides: object) -> Case:
    data: dict[str, object] = {
        "id": "C-1",
        "received_at": date(2025, 3, 4),
        "make": "Make A",
        "model": "Model B",
        "year": 2022,
        "component": "Instrument cluster display",
        "group": "display",
        "narrative": NARRATIVE,
        "safety_relevant": True,
    }
    data.update(overrides)
    return Case.model_validate(data)


def _extraction(*, clues: tuple[Clue, ...]) -> Extraction:
    return Extraction(case_id="C-1", group="display", clues=clues)


def _metrics(
    run: CaseRun,
    *,
    truth: Case | None = None,
    labels: bool = False,
):  # type: ignore[no-untyped-def]
    case = truth if truth is not None else run.case
    return compute_metrics(
        runs=[run],
        truth_cases=[case],
        proposals=[],
        issues=[],
        eight_d=[],
        memos=[],
        sources=SourceIndex(cases={run.case.id: NARRATIVE}),
        events=[],
        evaluation_labels_in_model_input=labels,
    )


def test_evaluation_labels_in_the_input_withhold_the_group_and_safety_numbers() -> None:
    case = _case()
    run = CaseRun(
        case=case,
        trace=(),
        extraction=_extraction(
            clues=(Clue(kind=ClueKind.SYMPTOM, quote="goes blank when the cabin is cold"),)
        ),
    )

    metrics = _metrics(run, labels=True)

    assert metrics.evaluation_labels_in_model_input is True
    assert metrics.group_macro_f1 is None
    assert metrics.group_coverage is None
    assert metrics.safety_precision is None
    assert metrics.safety_recall is None
    # The evidence metrics do not depend on the labels and stay reported.
    assert metrics.quote_grounding_rate is not None
    assert metrics.quote_grounding_rate.value == 1.0


def test_a_clean_run_reports_the_group_and_safety_numbers() -> None:
    case = _case(safety_relevant=False)
    run = CaseRun(
        case=case,
        trace=(),
        extraction=_extraction(
            clues=(Clue(kind=ClueKind.SYMPTOM, quote="goes blank when the cabin is cold"),)
        ),
    )

    metrics = _metrics(run)

    assert metrics.evaluation_labels_in_model_input is False
    assert metrics.group_macro_f1 is not None
    assert metrics.safety_recall is not None


def test_quotes_dropped_by_the_desk_stay_in_the_denominator() -> None:
    case = _case()
    trace = (
        TraceStep(
            step=1,
            agent="intake",
            action="verify_quotes",
            started_at=CREATED,
            tool="verify_quotes",
            tool_input={"quotes": ["a", "b"]},
            tool_output={"checked": 2, "verified": 1, "dropped": 1},
        ),
    )
    run = CaseRun(
        case=case,
        trace=trace,
        extraction=_extraction(
            clues=(Clue(kind=ClueKind.SYMPTOM, quote="goes blank when the cabin is cold"),)
        ),
    )

    metrics = _metrics(run)

    assert metrics.quote_grounding_rate is not None
    # One kept quote plus one dropped quote: the share is over what the model
    # proposed, not over the survivors.
    assert metrics.quote_grounding_rate.n == 2
    assert metrics.quote_grounding_rate.value == 0.5
    assert metrics.quotes_dropped == 1


def test_an_unverified_kept_quote_counts_against_the_share() -> None:
    case = _case()
    run = CaseRun(
        case=case,
        trace=(),
        extraction=_extraction(
            clues=(
                Clue(kind=ClueKind.SYMPTOM, quote="goes blank when the cabin is cold"),
                Clue(kind=ClueKind.OTHER, quote="the dealer refused to help"),
            )
        ),
    )

    metrics = _metrics(run)

    assert metrics.quote_grounding_rate is not None
    assert metrics.quote_grounding_rate.n == 2
    assert metrics.quote_grounding_rate.value == 0.5
