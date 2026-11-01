"""Tests for the keyword rule set that defines the linear baseline."""

from __future__ import annotations

from pathlib import Path

import pytest

from field_quality_agents.baseline.keywords import (
    KeywordGroup,
    KeywordRules,
    load_keywords,
    normalise_tokens,
    parse_keywords,
    safety_flag,
    sort_component,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
KEYWORDS = REPO_ROOT / "config" / "keywords.toml"


@pytest.fixture(scope="module")
def rules() -> KeywordRules:
    return load_keywords(KEYWORDS)


def test_committed_rules_load_with_all_groups(rules: KeywordRules) -> None:
    assert rules.source == KEYWORDS
    assert rules.version == "v1"
    assert rules.unclear == "unclear"
    assert rules.fallback == "electrical_general"
    assert rules.group_ids == (
        "adas",
        "ev_propulsion",
        "infotainment",
        "instrumentation",
        "restraints",
        "lighting",
        "safety_systems",
        "body_controls",
        "power_and_wiring",
        "electrical_general",
    )
    assert rules.safety_keywords


def test_normalise_tokens_is_lowercase_alphanumeric() -> None:
    assert normalise_tokens("ABS: 12V/24V battery!") == ("abs", "12v", "24v", "battery")


@pytest.mark.parametrize(
    ("component", "narrative", "expected"),
    [
        ("FORWARD COLLISION AVOIDANCE: ADAPTIVE CRUISE CONTROL", "", "adas"),
        ("LANE DEPARTURE: BLIND SPOT DETECTION", "", "adas"),
        ("BACK OVER PREVENTION", "", "adas"),
        ("HYBRID PROPULSION SYSTEM", "", "ev_propulsion"),
        ("ELECTRICAL SYSTEM:PROPULSION SYSTEM:TRACTION BATTERY", "", "ev_propulsion"),
        ("EQUIPMENT:ELECTRICAL:INFOTAINMENT", "", "infotainment"),
        ("EQUIPMENT:APPLIANCE:TV/RADIO/SPEAKERS", "", "infotainment"),
        ("ELECTRICAL SYSTEM:INSTRUMENT PANEL:SPEEDOMETER", "", "instrumentation"),
        ("AIR BAGS", "", "restraints"),
        ("SEAT BELTS", "", "restraints"),
        ("EXTERIOR LIGHTING:HEADLIGHTS", "", "lighting"),
        ("ELECTRONIC STABILITY CONTROL (ESC)", "", "safety_systems"),
        ("TIRES:PRESSURE MONITORING AND REGULATING SYSTEMS", "", "safety_systems"),
        ("VISIBILITY/WIPER", "", "body_controls"),
        ("ELECTRICAL SYSTEM:HORN", "", "body_controls"),
        ("ELECTRICAL SYSTEM:WIRING", "", "power_and_wiring"),
        ("ELECTRICAL SYSTEM:12V/24V/48V BATTERY", "", "power_and_wiring"),
        ("ELECTRICAL SYSTEM:IGNITION:COIL:SPARK PLUGS", "", "power_and_wiring"),
    ],
)
def test_component_sort_matches_expected_group(
    rules: KeywordRules, component: str, narrative: str, expected: str
) -> None:
    match = sort_component(component, narrative, rules)
    assert match.group == expected
    assert match.keywords
    assert not match.unclear


def test_fallback_only_when_nothing_specific_matches(rules: KeywordRules) -> None:
    generic = sort_component("ELECTRICAL SYSTEM", "An electrical fault.", rules)
    assert generic.group == "electrical_general"

    specific = sort_component("ELECTRICAL SYSTEM", "The battery dies overnight.", rules)
    assert specific.group == "power_and_wiring"


def test_unmapped_text_sorts_to_unclear(rules: KeywordRules) -> None:
    match = sort_component("ENGINE", "The engine misfires when cold.", rules)
    assert match.group == "unclear"
    assert match.keywords == ()
    assert match.score == 0
    assert match.unclear


def test_component_hits_outrank_narrative_hits(rules: KeywordRules) -> None:
    # The component says restraints; the narrative mentions a battery in
    # passing. The component signal must win.
    match = sort_component(
        "AIR BAGS",
        "After the battery was replaced the airbag light stayed on.",
        rules,
    )
    assert match.group == "restraints"


def test_matching_is_whole_token_only(rules: KeywordRules) -> None:
    assert sort_component("ENGINE", "It absolutely refuses to start.", rules).group == "unclear"
    assert sort_component("ENGINE", "The ABS pump runs.", rules).group == "safety_systems"


def test_ties_go_to_the_earlier_group() -> None:
    rules = KeywordRules(
        version="test",
        unclear="unclear",
        fallback="unclear",
        groups=(
            KeywordGroup(id="first", keywords=("shared phrase",)),
            KeywordGroup(id="second", keywords=("shared phrase",)),
        ),
        safety_keywords=("fire",),
        source=Path("test.toml"),
    )
    assert sort_component("", "a shared phrase here", rules).group == "first"


def test_safety_flag_uses_whole_phrases(rules: KeywordRules) -> None:
    flagged = safety_flag("", "The vehicle caught fire while parked.", rules)
    assert flagged.safety_relevant
    assert "caught fire" in flagged.keywords

    not_flagged = safety_flag("ENGINE", "The firewall has a rattle.", rules)
    assert not not_flagged.safety_relevant
    assert not_flagged.keywords == ()


def test_keywords_are_recorded_for_the_decision(rules: KeywordRules) -> None:
    match = sort_component("ELECTRICAL SYSTEM:WIRING", "Battery cable corrosion.", rules)
    assert "wiring" in match.keywords


def test_duplicate_group_ids_are_rejected() -> None:
    document: dict[str, object] = {
        "version": "v1",
        "safety": {"keywords": ["fire"]},
        "group": [
            {"id": "one", "keywords": ["a"]},
            {"id": "one", "keywords": ["b"]},
        ],
    }
    with pytest.raises(ValueError, match="duplicate group id"):
        parse_keywords(document, source=Path("test.toml"))


def test_unknown_fallback_is_rejected() -> None:
    document: dict[str, object] = {
        "version": "v1",
        "fallback": "missing",
        "safety": {"keywords": ["fire"]},
        "group": [{"id": "one", "keywords": ["a"]}],
    }
    with pytest.raises(ValueError, match="fallback"):
        parse_keywords(document, source=Path("test.toml"))


def test_missing_safety_keywords_are_rejected() -> None:
    document: dict[str, object] = {
        "version": "v1",
        "safety": {},
        "group": [{"id": "one", "keywords": ["a"]}],
    }
    with pytest.raises(ValueError, match=r"safety\.keywords"):
        parse_keywords(document, source=Path("test.toml"))
