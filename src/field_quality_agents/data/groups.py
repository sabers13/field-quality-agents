"""Component groups and the single-group rule.

The groups are curated from the component-description value counts in the
snapshot and live in ``data/groups.toml``. A component maps to the group with
the longest normalised prefix, so a specific prefix such as
``ELECTRICAL SYSTEM:ADAS`` wins over the generic ``ELECTRICAL SYSTEM``.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "Group",
    "GroupIndex",
    "load_groups",
    "map_component",
    "map_group",
    "normalise_component",
    "prefix_index",
]

MIN_GROUPS = 8
MAX_GROUPS = 12


@dataclass(frozen=True)
class Group:
    id: str
    description: str
    prefixes: tuple[str, ...]


GroupIndex = tuple[tuple[str, str], ...]


def normalise_component(text: str) -> str:
    """Upper-case, trim and remove whitespace around colons."""
    value = " ".join(text.upper().split())
    return re.sub(r"\s*:\s*", ":", value)


def load_groups(path: Path = Path("data/groups.toml")) -> dict[str, Group]:
    """Load and validate the committed group file."""
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    entries = raw.get("group")
    if not isinstance(entries, list):
        raise ValueError(f"{path}: expected a 'group' array")
    groups: dict[str, Group] = {}
    seen_prefixes: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: each group must be a table")
        group_id = entry.get("id")
        description = entry.get("description")
        prefixes = entry.get("prefixes")
        if not isinstance(group_id, str) or not group_id.strip():
            raise ValueError(f"{path}: group id must be a non-empty string")
        if group_id in groups:
            raise ValueError(f"{path}: duplicate group id {group_id!r}")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"{path}: group {group_id!r} needs a description")
        if not isinstance(prefixes, list) or not prefixes:
            raise ValueError(f"{path}: group {group_id!r} needs prefixes")
        cleaned: list[str] = []
        for prefix in prefixes:
            if not isinstance(prefix, str) or not prefix.strip():
                raise ValueError(f"{path}: group {group_id!r} has an empty prefix")
            normalised = normalise_component(prefix)
            if normalised in seen_prefixes:
                raise ValueError(
                    f"{path}: prefix {prefix!r} appears in both "
                    f"{seen_prefixes[normalised]!r} and {group_id!r}"
                )
            seen_prefixes[normalised] = group_id
            cleaned.append(prefix)
        groups[group_id] = Group(
            id=group_id,
            description=description.strip(),
            prefixes=tuple(cleaned),
        )
    if not MIN_GROUPS <= len(groups) <= MAX_GROUPS:
        raise ValueError(
            f"{path}: expected {MIN_GROUPS}-{MAX_GROUPS} groups, found {len(groups)}"
        )
    return groups


def prefix_index(groups: Mapping[str, Group]) -> GroupIndex:
    """Return ``(normalised prefix, group id)`` sorted longest first."""
    items = [
        (normalise_component(prefix), group_id)
        for group_id, group in groups.items()
        for prefix in group.prefixes
    ]
    items.sort(key=lambda item: (-len(item[0]), item[0], item[1]))
    return tuple(items)


def map_component(component: str, index: GroupIndex) -> str | None:
    """Map one component description to a group id, or ``None``."""
    value = normalise_component(component)
    if not value:
        return None
    for prefix, group_id in index:
        if value.startswith(prefix):
            return group_id
    return None


def map_group(component: str, groups: Mapping[str, Group]) -> str | None:
    """Map one component description using the groups mapping."""
    return map_component(component, prefix_index(groups))
