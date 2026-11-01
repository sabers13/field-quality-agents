"""Typed DuckDB tools over the committed field-quality data.

This module is the public surface named in ``docs/INTERFACES.md`` §Q2. Each
function delegates to the process-wide :class:`~field_quality_agents.tools.db.Toolbox`,
which can be replaced with :func:`configure` for the MCP server or a fixture
DuckDB in tests.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from field_quality_agents.contracts import Case, Clue
from field_quality_agents.tools import cluster, lookup, rules, search
from field_quality_agents.tools import quotes as quotes_module
from field_quality_agents.tools.db import (
    Toolbox,
    configure,
    get_toolbox,
    reset_default,
)
from field_quality_agents.tools.models import (
    CaseFilters,
    ClusterStats,
    QuoteVerification,
    SimilarCase,
)

__all__ = [
    "CaseFilters",
    "ClusterStats",
    "QuoteVerification",
    "SimilarCase",
    "Toolbox",
    "case_lookup",
    "cluster_stats",
    "configure",
    "get_toolbox",
    "investigations_for",
    "recalls_for",
    "reset_default",
    "rulebook",
    "similar_cases",
    "verify_quotes",
]


def similar_cases(
    text: str,
    filters: CaseFilters | None = None,
    k: int = 10,
) -> list[SimilarCase]:
    """BM25 search over the knowledge base, best score first, ties by id."""

    return search.similar_cases(get_toolbox(), text, filters, k)


def recalls_for(make: str, model: str, year: int, group: str) -> list[dict[str, object]]:
    """Matching recalls, newest open date first, then id."""

    return lookup.recalls_for(get_toolbox(), make, model, year, group)


def investigations_for(
    make: str,
    model: str,
    year: int,
    group: str,
) -> list[dict[str, object]]:
    """Matching investigations, newest open date first, then id."""

    return lookup.investigations_for(get_toolbox(), make, model, year, group)


def cluster_stats(
    make: str,
    model: str,
    year: int,
    group: str,
    until_date: date,
) -> ClusterStats:
    """Weekly counts, trailing mean and the Poisson spike state."""

    return cluster.cluster_stats(get_toolbox(), make, model, year, group, until_date)


def verify_quotes(text: str, quotes: Sequence[Clue]) -> list[QuoteVerification]:
    """Check each quote as a verbatim span after whitespace normalisation."""

    return quotes_module.verify_quotes(text, quotes)


def rulebook(conditions: Sequence[str]) -> list[dict[str, object]]:
    """Map reported conditions to targeted tests from the example rulebook."""

    return rules.rulebook(get_toolbox().rulebook_path, conditions)


def case_lookup(id: str) -> Case | None:
    """Return one case from the knowledge base or replay set."""

    return lookup.case_lookup(get_toolbox(), id)
