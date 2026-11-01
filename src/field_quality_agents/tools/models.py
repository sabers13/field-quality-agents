"""Typed inputs and outputs for the DuckDB tool layer.

These shapes mirror ``docs/INTERFACES.md`` §Q2. They are plain dataclasses so
the agent graph, the MCP server and the API can all use the same objects
without a serialisation round-trip.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from field_quality_agents.contracts import WeekCount

__all__ = [
    "CaseFilters",
    "ClusterStats",
    "QuoteVerification",
    "SimilarCase",
]


@dataclass(frozen=True)
class CaseFilters:
    """Optional equality filters for :func:`similar_cases`."""

    make: str | None = None
    model: str | None = None
    year: int | None = None
    group: str | None = None
    safety_relevant: bool | None = None


@dataclass(frozen=True)
class SimilarCase:
    id: str
    score: float
    make: str
    model: str
    year: int
    group: str
    excerpt: str


@dataclass(frozen=True)
class ClusterStats:
    make: str
    model: str
    year: int
    group: str
    until_date: date
    weekly: tuple[WeekCount, ...]
    trailing_mean: float
    threshold: float
    observed: int
    spike: bool


@dataclass(frozen=True)
class QuoteVerification:
    quote: str
    verified: bool
