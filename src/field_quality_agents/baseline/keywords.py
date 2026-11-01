"""Keyword rules for the linear "before" pipeline.

The rules live in ``config/keywords.toml`` and are loaded without any model
call. Matching is deterministic and whole-token only: a keyword phrase matches
as a contiguous run of lower-case alphanumeric tokens, so ``abs`` does not
match ``absolutely``.

Two scoring rules keep the sort honest:

- a hit in the component text counts three times the phrase length, a hit in
  the narrative counts once;
- the configured ``fallback`` group is considered only when no other group
  matches, so a generic "electrical system" report does not outrank a specific
  group.

The best score wins; ties go to the earlier group in the file. A report with no
match sorts to ``unclear``.
"""

from __future__ import annotations

import os
import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "DEFAULT_KEYWORDS_PATH",
    "KeywordGroup",
    "KeywordMatch",
    "KeywordRules",
    "SafetyMatch",
    "load_keywords",
    "normalise_tokens",
    "safety_flag",
    "sort_component",
]

DEFAULT_KEYWORDS_PATH = Path("config/keywords.toml")

_TOKEN_RE = re.compile(r"[a-z0-9]+")

#: Component hits are the stronger signal: the component field is short and
#: names the part, while a narrative mentions many parts in passing.
_COMPONENT_WEIGHT = 3
_NARRATIVE_WEIGHT = 1


@dataclass(frozen=True)
class KeywordGroup:
    """One component group and its keyword phrases."""

    id: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class KeywordRules:
    """The whole linear rule set, loaded from ``config/keywords.toml``."""

    version: str
    unclear: str
    fallback: str
    groups: tuple[KeywordGroup, ...]
    safety_keywords: tuple[str, ...]
    source: Path

    @property
    def group_ids(self) -> tuple[str, ...]:
        return tuple(group.id for group in self.groups)


@dataclass(frozen=True)
class KeywordMatch:
    """The component sort for one report."""

    group: str
    keywords: tuple[str, ...]
    score: int

    @property
    def unclear(self) -> bool:
        return not self.keywords


@dataclass(frozen=True)
class SafetyMatch:
    """The keyword safety flag for one report."""

    safety_relevant: bool
    keywords: tuple[str, ...]


def normalise_tokens(text: str) -> tuple[str, ...]:
    """Lower-case text and split it into alphanumeric tokens."""

    return tuple(_TOKEN_RE.findall(text.lower()))


def _contains(tokens: Sequence[str], phrase: Sequence[str]) -> bool:
    """True when ``phrase`` occurs as a contiguous run of whole tokens."""

    if not phrase:
        return False
    width = len(phrase)
    first = phrase[0]
    for start in range(len(tokens) - width + 1):
        if tokens[start] == first and tuple(tokens[start : start + width]) == tuple(phrase):
            return True
    return False


def _phrases(keywords: Sequence[str]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple((keyword, normalise_tokens(keyword)) for keyword in keywords)


def _score_group(
    component: Sequence[str],
    narrative: Sequence[str],
    keywords: Sequence[str],
) -> tuple[int, tuple[str, ...]]:
    score = 0
    matched: list[str] = []
    for phrase, tokens in _phrases(keywords):
        length = len(tokens)
        component_hit = _contains(component, tokens)
        narrative_hit = _contains(narrative, tokens)
        if component_hit:
            score += _COMPONENT_WEIGHT * length
        if narrative_hit:
            score += _NARRATIVE_WEIGHT * length
        if component_hit or narrative_hit:
            matched.append(phrase)
    return score, tuple(matched)


def sort_component(
    component: str,
    narrative: str,
    rules: KeywordRules,
) -> KeywordMatch:
    """Sort one report to the best-scoring component group."""

    component_tokens = normalise_tokens(component)
    narrative_tokens = normalise_tokens(narrative)

    best_group = rules.unclear
    best_keywords: tuple[str, ...] = ()
    best_score = 0
    for group in rules.groups:
        if group.id == rules.fallback:
            continue
        score, matched = _score_group(component_tokens, narrative_tokens, group.keywords)
        if score > best_score:
            best_group = group.id
            best_keywords = matched
            best_score = score

    if best_score == 0:
        for group in rules.groups:
            if group.id != rules.fallback:
                continue
            score, matched = _score_group(component_tokens, narrative_tokens, group.keywords)
            if score > 0:
                best_group = group.id
                best_keywords = matched
                best_score = score

    return KeywordMatch(group=best_group, keywords=best_keywords, score=best_score)


def safety_flag(component: str, narrative: str, rules: KeywordRules) -> SafetyMatch:
    """Raise the keyword safety flag when any safety phrase occurs."""

    text = normalise_tokens(f"{component} {narrative}")
    matched: list[str] = []
    for phrase, tokens in _phrases(rules.safety_keywords):
        if _contains(text, tokens):
            matched.append(phrase)
    return SafetyMatch(safety_relevant=bool(matched), keywords=tuple(matched))


def _default_path() -> Path:
    explicit = os.environ.get("FQA_KEYWORDS")
    if explicit:
        return Path(explicit)
    candidates = (
        Path.cwd() / DEFAULT_KEYWORDS_PATH,
        Path(__file__).resolve().parents[3] / DEFAULT_KEYWORDS_PATH,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def _as_str(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"keywords: {field} must be a non-empty string")
    return value.strip()


def _as_str_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"keywords: {field} must be a non-empty list")
    items: list[str] = []
    for item in value:
        items.append(_as_str(item, field=field))
    return tuple(items)


def _table(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"keywords: {field} must be a table")
    return value


def parse_keywords(document: Mapping[str, object], *, source: Path) -> KeywordRules:
    """Validate a parsed TOML document and return typed rules."""

    version = _as_str(document.get("version", "v1"), field="version")
    unclear = _as_str(document.get("unclear", "unclear"), field="unclear")
    fallback = _as_str(document.get("fallback", unclear), field="fallback")

    safety_table = _table(document.get("safety"), field="safety")
    safety_keywords = _as_str_tuple(safety_table.get("keywords"), field="safety.keywords")

    raw_groups = document.get("group")
    if not isinstance(raw_groups, list) or not raw_groups:
        raise ValueError("keywords: group must be a non-empty array of tables")

    groups: list[KeywordGroup] = []
    seen: set[str] = set()
    for position, raw_group in enumerate(raw_groups):
        table = _table(raw_group, field=f"group[{position}]")
        group_id = _as_str(table.get("id"), field=f"group[{position}].id")
        if group_id in seen:
            raise ValueError(f"keywords: duplicate group id {group_id!r}")
        seen.add(group_id)
        groups.append(
            KeywordGroup(
                id=group_id,
                keywords=_as_str_tuple(
                    table.get("keywords"), field=f"group[{position}].keywords"
                ),
            )
        )

    if unclear in seen:
        raise ValueError("keywords: unclear must not be a group id")
    if fallback != unclear and fallback not in seen:
        raise ValueError("keywords: fallback must name a group or the unclear label")

    return KeywordRules(
        version=version,
        unclear=unclear,
        fallback=fallback,
        groups=tuple(groups),
        safety_keywords=safety_keywords,
        source=source,
    )


def load_keywords(path: str | Path | None = None) -> KeywordRules:
    """Load and validate ``config/keywords.toml``."""

    resolved = Path(path) if path is not None else _default_path()
    with resolved.open("rb") as handle:
        document = tomllib.load(handle)
    return parse_keywords(document, source=resolved)
