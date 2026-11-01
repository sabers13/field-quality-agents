"""The fixed showcase rules in ``export/showcase.py``."""

from __future__ import annotations

import json
from pathlib import Path

from field_quality_agents.export.showcase import choose_examples


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _run(tmp_path: Path) -> tuple[Path, Path]:
    run = tmp_path / "runs" / "replay"
    baseline = tmp_path / "baseline"
    _write(
        run / "issues.json",
        [
            {
                "id": "I-OLD",
                "opened_at": "2025-02-17",
                "linked_case_ids": ["c-old"],
                "linked_recall_ids": [],
                "linked_investigation_ids": ["PE-OLD"],
            },
            {
                "id": "I-EARLY",
                "opened_at": "2025-07-11",
                "linked_case_ids": ["c-early"],
                "linked_recall_ids": ["25V000000"],
                "linked_investigation_ids": [],
            },
            {
                "id": "I-LATE",
                "opened_at": "2025-09-16",
                "linked_case_ids": ["c-late"],
                "linked_recall_ids": ["25V999999"],
                "linked_investigation_ids": [],
            },
        ],
    )
    _write(
        run / "evidence.json",
        {
            "c-old": {
                "recalls": [],
                "investigations": [{"id": "PE-OLD", "open_date": "2024-05-08"}],
            },
            "c-early": {
                "recalls": [{"id": "25V000000", "open_date": "2025-09-15"}],
                "investigations": [],
            },
            "c-late": {
                "recalls": [{"id": "25V999999", "open_date": "2026-01-01"}],
                "investigations": [],
            },
        },
    )
    _write(
        run / "traces.json",
        {
            "c-short": [{"step": 1}],
            "c-long": [{"step": 1}, {"step": 2}, {"step": 3}],
        },
    )
    _write(
        run / "proposals.json",
        {
            "c-short": {"kind": "targeted_load_test", "evidence": []},
            "c-long": {"kind": "targeted_load_test", "evidence": []},
            "c-missed": {
                "kind": "targeted_load_test",
                "evidence": [{"verified": True, "quote": "smoke from the loom"}],
            },
        },
    )
    _write(
        run / "cases.json",
        [
            {"id": "c-missed", "received_at": "2025-03-01"},
            {"id": "c-reverse", "received_at": "2025-03-02"},
        ],
    )
    _write(
        baseline / "decisions.json",
        [
            {"case_id": "c-missed", "closed_no_trouble_found": True},
            {"case_id": "c-reverse", "closed_no_trouble_found": True},
        ],
    )
    return run, baseline


def test_picks_the_three_fixed_examples_and_the_reverse(tmp_path: Path) -> None:
    run, baseline = _run(tmp_path)
    examples = choose_examples(run, baseline)

    assert [example.note for example in examples] == [
        "The earliest issue that preceded a matching recall or investigation.",
        "The longest agent trace that ended in a targeted test.",
        "Where the linear pipeline missed what the agent found.",
        "Reverse: where the linear pipeline was right too.",
    ]
    fleet, targeted, missed, reverse = examples
    # I-OLD's investigation is before it; I-EARLY precedes a recall by 66 days.
    assert fleet.case_id == "c-early"
    assert "66 days before" in fleet.after
    assert "recall 25V000000" in fleet.after
    assert targeted.case_id == "c-long"
    assert "3 trace steps" in targeted.after
    assert missed.case_id == "c-missed"
    assert reverse.case_id == "c-reverse"


def test_returns_nothing_without_a_run(tmp_path: Path) -> None:
    assert choose_examples(tmp_path / "missing", tmp_path / "baseline") == []


def test_falls_back_to_the_earliest_issue_without_a_following_event(tmp_path: Path) -> None:
    run = tmp_path / "run"
    _write(
        run / "issues.json",
        [
            {
                "id": "I-ONLY",
                "opened_at": "2025-01-02",
                "linked_case_ids": ["c1"],
                "linked_recall_ids": [],
                "linked_investigation_ids": [],
            }
        ],
    )
    examples = choose_examples(run, tmp_path / "baseline")
    assert [example.note for example in examples] == [
        "The earliest issue in the run; no matching recall or investigation followed it yet."
    ]
