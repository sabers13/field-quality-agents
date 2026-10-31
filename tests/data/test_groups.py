"""Component groups and the longest-prefix rule."""

from __future__ import annotations

from pathlib import Path

import pytest

from field_quality_agents.data.groups import (
    MAX_GROUPS,
    MIN_GROUPS,
    Group,
    load_groups,
    map_group,
    normalise_component,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def groups() -> dict[str, Group]:
    return load_groups(REPO_ROOT / "data" / "groups.toml")


def test_group_file_has_the_documented_shape(groups: dict[str, Group]) -> None:
    assert MIN_GROUPS <= len(groups) <= MAX_GROUPS
    assert all(group.description for group in groups.values())
    assert all(group.prefixes for group in groups.values())
    prefixes = [prefix for group in groups.values() for prefix in group.prefixes]
    assert len(prefixes) == len(set(prefixes))


def test_normalise_component_removes_spacing_around_colons() -> None:
    assert normalise_component("  electrical system:  instrument panel ") == (
        "ELECTRICAL SYSTEM:INSTRUMENT PANEL"
    )


@pytest.mark.parametrize(
    ("component", "group_id"),
    [
        ("ELECTRICAL SYSTEM:WIRING", "power_and_wiring"),
        ("ELECTRICAL SYSTEM:12V/24V/48V BATTERY:CABLES", "power_and_wiring"),
        ("ELECTRICAL SYSTEM:IGNITION:COIL:SPARK PLUGS", "power_and_wiring"),
        ("ELECTRICAL SYSTEM:ADAS:AUTONOMOUS/SELF DRIVING", "adas"),
        ("FORWARD COLLISION AVOIDANCE: AUTOMATIC EMERGENCY BRAKING", "adas"),
        ("LANE DEPARTURE: BLIND SPOT DETECTION", "adas"),
        ("ELECTRICAL SYSTEM: INSTRUMENT CLUSTER/PANEL", "instrumentation"),
        ("ELECTRICAL SYSTEM:PROPULSION SYSTEM:TRACTION BATTERY", "ev_propulsion"),
        ("HYBRID PROPULSION SYSTEM", "ev_propulsion"),
        ("EQUIPMENT:ELECTRICAL:INFOTAINMENT", "infotainment"),
        ("COMMUNICATION: AUTO CRASH NOTIFICATION", "infotainment"),
        ("EXTERIOR LIGHTING:BRAKE LIGHTS", "lighting"),
        ("VISIBILITY:POWER WINDOW DEVICES AND CONTROLS", "body_controls"),
        ("ELECTRONIC STABILITY CONTROL (ESC)", "safety_systems"),
        ("AIR BAGS", "restraints"),
        ("ELECTRICAL SYSTEM", "electrical_general"),
    ],
)
def test_map_group_uses_the_longest_prefix(
    groups: dict[str, Group], component: str, group_id: str
) -> None:
    assert map_group(component, groups) == group_id


def test_unknown_components_do_not_map(groups: dict[str, Group]) -> None:
    assert map_group("ENGINE", groups) is None
    assert map_group("", groups) is None
    assert map_group("POWER TRAIN:AUTOMATIC TRANSMISSION", groups) is None
