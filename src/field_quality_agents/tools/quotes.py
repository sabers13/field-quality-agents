"""Verbatim quote checking.

A quote is evidence only when it appears in the source after whitespace is
normalised. Case, punctuation and wording must match exactly: there is no
fuzzy or substring-with-different-case fallback, because the citation would
not be defensible.

Two further rules keep a trivial match from counting as evidence:

* the span must be meaningful — at least two words, or an identifier such as a
  fault code or a recall campaign number (a digit and four characters);
* the match must fall on a word boundary, so ``car`` is not "found" inside
  ``carpet``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from field_quality_agents.contracts import Clue
from field_quality_agents.tools.models import QuoteVerification

__all__ = ["quote_is_grounded", "verify_quotes"]

_WHITESPACE = re.compile(r"\s+")

#: A span of one ordinary word ("the", "car", "failure") is not evidence.
_MIN_WORDS = 2

#: Identifiers are one word but carry a digit: "21V-035", "P0302", "P1A9096".
_MIN_IDENTIFIER_CHARS = 4


def _normalise(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def _is_meaningful(needle: str) -> bool:
    if len(needle.split()) >= _MIN_WORDS:
        return True
    return (
        len(needle) >= _MIN_IDENTIFIER_CHARS
        and any(character.isdigit() for character in needle)
    )


def quote_is_grounded(quote: str | None, text: str) -> bool:
    """True when ``quote`` is a meaningful, word-bounded verbatim span of ``text``."""

    if not quote:
        return False
    needle = _normalise(quote)
    if not needle or not _is_meaningful(needle):
        return False
    body = _normalise(text)
    pattern = r"(?<![0-9A-Za-z])" + re.escape(needle) + r"(?![0-9A-Za-z])"
    return re.search(pattern, body) is not None


def verify_quotes(text: str, quotes: Sequence[Clue]) -> list[QuoteVerification]:
    checks: list[QuoteVerification] = []
    for clue in quotes:
        checks.append(
            QuoteVerification(
                quote=clue.quote,
                verified=quote_is_grounded(clue.quote, text),
            )
        )
    return checks
