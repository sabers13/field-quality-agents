from __future__ import annotations

from pathlib import Path

import pytest

from field_quality_agents.tools import Toolbox, rulebook
from field_quality_agents.tools.rules import load_rules


def test_every_example_condition_maps_to_a_targeted_test() -> None:
    expected = {
        "moisture": "Humidity and condensation test",
        "cold": "Low-temperature cycling test",
        "heat": "High-temperature operation test",
        "vibration": "Vibration test",
        "intermittent": "Long-run power cycling test",
        "after service": "Installation check before test",
        "charging": "Electrical load test",
    }
    for condition, test in expected.items():
        matches = rulebook([condition])
        assert [match["test"] for match in matches] == [test]


def test_matching_is_case_insensitive_and_whole_word() -> None:
    assert [match["id"] for match in rulebook(["COLD"])] == ["cold"]
    assert rulebook(["scold"]) == []
    assert rulebook(["cheat"]) == []


def test_multiple_conditions_and_synonyms() -> None:
    matches = rulebook(["cold", "water ingress", "rough roads"])
    assert [match["id"] for match in matches] == ["moisture", "cold", "vibration"]
    assert matches[0]["matched_conditions"] == ["water ingress"]
    assert matches[2]["matched_conditions"] == ["rough roads"]


def test_one_condition_can_match_more_than_one_rule() -> None:
    matches = rulebook(["after service in cold weather"])
    assert [match["id"] for match in matches] == ["cold", "after_service"]


def test_no_conditions_and_no_match() -> None:
    assert rulebook([]) == []
    assert rulebook([""]) == []
    assert rulebook(["unrelated complaint"]) == []


def test_replaced_part_counts_as_after_service() -> None:
    matches = rulebook(["the battery was replaced"])
    assert [match["id"] for match in matches] == ["after_service"]
    assert matches[0]["matched_conditions"] == ["the battery was replaced"]


def test_result_shape() -> None:
    match = rulebook(["moisture"])[0]
    assert set(match) == {"id", "test", "reason", "matched_conditions"}
    assert isinstance(match["reason"], str)
    assert match["reason"]


def test_load_rules_reads_seven_rules(toolbox: Toolbox) -> None:
    rules = load_rules(toolbox.rulebook_path)
    assert [rule.id for rule in rules] == [
        "moisture",
        "cold",
        "heat",
        "vibration",
        "intermittent",
        "after_service",
        "charging",
    ]
    assert all(rule.conditions for rule in rules)


def test_invalid_rulebook_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text(
        '[[rule]]\nid = "x"\ntest = "T"\nreason = "R"\nconditions = []\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="conditions"):
        load_rules(path)
