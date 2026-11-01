from __future__ import annotations

from field_quality_agents.tools import case_lookup, investigations_for, recalls_for


def test_recalls_for_returns_newest_first() -> None:
    recalls = recalls_for("FORD", "F-150", 2021, "body_controls")
    assert [recall["id"] for recall in recalls] == ["r02", "r01"]
    assert recalls[0]["open_date"] == "2024-02-01"
    assert set(recalls[0]) == {
        "id",
        "make",
        "model",
        "year",
        "component",
        "group",
        "summary",
        "open_date",
    }


def test_recalls_for_excludes_other_group_and_year() -> None:
    ids = [recall["id"] for recall in recalls_for("FORD", "F-150", 2021, "body_controls")]
    assert "r03" not in ids  # other group
    assert "r05" not in ids  # other model year
    assert ids == ["r02", "r01"]


def test_recalls_for_is_case_insensitive() -> None:
    assert [row["id"] for row in recalls_for("ford", "f-150", 2021, "body_controls")] == [
        "r02",
        "r01",
    ]


def test_recalls_for_no_match() -> None:
    assert recalls_for("FORD", "F-150", 1999, "body_controls") == []


def test_investigations_for_returns_newest_first() -> None:
    investigations = investigations_for("FORD", "F-150", 2021, "body_controls")
    assert [item["id"] for item in investigations] == ["i01", "i02"]
    assert investigations[0]["open_date"] == "2024-01-15"


def test_investigations_for_excludes_other_keys() -> None:
    assert investigations_for("FORD", "F-150", 2021, "ev_propulsion") == []


def test_case_lookup_returns_a_contract_case() -> None:
    case = case_lookup("c01")
    assert case is not None
    assert case.id == "c01"
    assert case.make == "FORD"
    assert case.model == "F-150"
    assert case.year == 2021
    assert case.group == "body_controls"
    assert case.source_id == "c01"
    assert case.safety_relevant is False
    assert case.mileage == 12000
    assert case.status.value == "new"


def test_case_lookup_unknown_id() -> None:
    assert case_lookup("does-not-exist") is None
