"""Verbatim quote checking.

A quote is evidence only when it appears in the source after whitespace is
normalised. Case, punctuation and wording must match exactly: there is no
fuzzy or substring-with-different-case fallback, because the citation would
not be defensible.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from field_quality_agents.contracts import Clue
from field_quality_agents.tools.models import QuoteVerification

__all__ = ["verify_quotes"]

_WHITESPACE = re.compile(r"\s+")


def _normalise(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def verify_quotes(text: str, quotes: Sequence[Clue]) -> list[QuoteVerification]:
    body = _normalise(text)
    checks: list[QuoteVerification] = []
    for clue in quotes:
        needle = _normalise(clue.quote)
        checks.append(QuoteVerification(quote=clue.quote, verified=bool(needle) and needle in body))
    return checks
