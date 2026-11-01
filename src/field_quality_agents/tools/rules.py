"""Condition-to-test rules from ``config/rulebook.toml``.

The rulebook is an example, not a service manual. Matching is
case-insensitive and whole-word/phrase aware, so ``cold`` does not match
``scold`` and ``heat`` does not match ``cheat``. Rules are returned in file
order; each result names the input condition(s) that matched.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = ["Rule", "load_rules", "match_rules", "rulebook"]

_SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Rule:
    id: str
    test: str
    reason: str
    conditions: tuple[str, ...]


def _normalise(text: str) -> str:
    return _SPACE.sub(" ", text.strip().lower())


def _as_text(value: Any, field: str, index: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"rule {index}: {field} must be a non-empty string")
    return value.strip()


def _as_conditions(value: Any, index: int) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"rule {index}: conditions must be a non-empty list")
    conditions: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"rule {index}: every condition must be a non-empty string")
        conditions.append(item.strip())
    return tuple(conditions)


def load_rules(path: Path) -> list[Rule]:
    with path.open("rb") as handle:
        document = tomllib.load(handle)
    raw_rules = document.get("rule")
    if not isinstance(raw_rules, list):
        raise ValueError(f"{path}: expected one or more [[rule]] tables")
    rules: list[Rule] = []
    for index, raw in enumerate(raw_rules, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"rule {index}: expected a table")
        rules.append(
            Rule(
                id=_as_text(raw.get("id"), "id", index),
                test=_as_text(raw.get("test"), "test", index),
                reason=_as_text(raw.get("reason"), "reason", index),
                conditions=_as_conditions(raw.get("conditions"), index),
            )
        )
    return rules


def _matches(condition: str, keyword: str) -> bool:
    normalised_keyword = _normalise(keyword)
    if not normalised_keyword:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(normalised_keyword) + r"(?![a-z0-9])"
    return re.search(pattern, _normalise(condition)) is not None


def match_rules(rules: Sequence[Rule], conditions: Sequence[str]) -> list[dict[str, object]]:
    cleaned = [condition.strip() for condition in conditions if condition.strip()]
    results: list[dict[str, object]] = []
    for rule in rules:
        matched: list[str] = []
        for condition in cleaned:
            if any(_matches(condition, keyword) for keyword in rule.conditions) and (
                condition not in matched
            ):
                matched.append(condition)
        if matched:
            results.append(
                {
                    "id": rule.id,
                    "test": rule.test,
                    "reason": rule.reason,
                    "matched_conditions": matched,
                }
            )
    return results


def rulebook(path: Path, conditions: Sequence[str]) -> list[dict[str, object]]:
    if not conditions:
        return []
    return match_rules(load_rules(path), conditions)
