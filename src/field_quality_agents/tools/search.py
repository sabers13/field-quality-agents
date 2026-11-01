"""BM25 search over complaint narratives.

Scores are the classic Okapi BM25 with ``k1=1.2`` and ``b=0.75``. The corpus
statistics are computed over the filtered set, so a search inside one vehicle
key is scored against that key rather than against the whole knowledge base.
Results are rounded to four decimals before sorting, and ties are broken by
id, exactly as PLAN §8 requires.

The index is two temporary DuckDB tables built on first use: one document
table with lengths and one posting table. This keeps the search in DuckDB
without depending on an extension that would need a network install on a
fresh machine. A query against the real 40,000-case knowledge base builds the
index in roughly two seconds and answers in tens of milliseconds.
"""

from __future__ import annotations

import re
from typing import Any

from field_quality_agents.tools.db import Toolbox
from field_quality_agents.tools.models import CaseFilters, SimilarCase

__all__ = ["similar_cases", "tokenize"]

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_EXCERPT_LIMIT = 280

_STOPWORD_TEXT = (
    "a an and are as at be been but by can could did do does for from had has have "
    "he her his i if in into is it its may might must my no not of on or our she "
    "should than that the their them then there these they this those to was we "
    "were what when where which who will with would you your"
)
_STOPWORDS = frozenset(_STOPWORD_TEXT.split())


def tokenize(text: str) -> list[str]:
    """Lower-case word tokens, without stopwords, in sorted unique order."""

    return sorted({token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS})


def _excerpt(narrative: str) -> str:
    text = " ".join(narrative.split())
    if len(text) <= _EXCERPT_LIMIT:
        return text
    return text[:_EXCERPT_LIMIT].rstrip() + "..."


def _filter_sql(filters: CaseFilters | None) -> tuple[str, list[object]]:
    clauses: list[str] = []
    parameters: list[object] = []
    if filters is None:
        return "TRUE", parameters
    if filters.make is not None:
        clauses.append("upper(make) = upper(?)")
        parameters.append(filters.make)
    if filters.model is not None:
        clauses.append("upper(model) = upper(?)")
        parameters.append(filters.model)
    if filters.year is not None:
        clauses.append("year = ?")
        parameters.append(filters.year)
    if filters.group is not None:
        clauses.append('"group" = ?')
        parameters.append(filters.group)
    if filters.safety_relevant is not None:
        clauses.append("safety_relevant = ?")
        parameters.append(filters.safety_relevant)
    return (" AND ".join(clauses) if clauses else "TRUE"), parameters


_SEARCH_SQL = """
WITH filtered AS (
    SELECT id, narrative, dl
    FROM fqa_docs
    WHERE {filters}
),
query_terms AS (
    SELECT unnest(?::VARCHAR[]) AS term
),
baseline AS (
    SELECT avg(dl) AS mean_length, count(*) AS document_count
    FROM filtered
),
postings AS (
    SELECT tokens.id, tokens.token, count(*) AS term_frequency
    FROM fqa_tokens AS tokens
    JOIN filtered AS documents ON documents.id = tokens.id
    WHERE tokens.token IN (SELECT term FROM query_terms)
    GROUP BY tokens.id, tokens.token
),
term_stats AS (
    SELECT token, count(*) AS document_frequency
    FROM postings
    GROUP BY token
),
scored AS (
    SELECT postings.id,
           sum(
               ln(1 + (baseline.document_count - term_stats.document_frequency + 0.5)
                      / (term_stats.document_frequency + 0.5))
               * (postings.term_frequency * 2.2)
               / (postings.term_frequency
                  + 1.2 * (1 - 0.75
                           + 0.75 * documents.dl / nullif(baseline.mean_length, 0)))
           ) AS raw_score
    FROM postings
    JOIN filtered AS documents ON documents.id = postings.id
    JOIN term_stats ON term_stats.token = postings.token
    CROSS JOIN baseline
    GROUP BY postings.id
)
SELECT documents.id,
       documents.make,
       documents.model,
       documents.year,
       documents."group",
       documents.narrative,
       round(scored.raw_score, 4) AS score
FROM scored
JOIN fqa_docs AS documents ON documents.id = scored.id
ORDER BY score DESC, documents.id ASC
LIMIT ?
"""


def similar_cases(
    toolbox: Toolbox,
    text: str,
    filters: CaseFilters | None = None,
    k: int = 10,
) -> list[SimilarCase]:
    if k <= 0:
        return []
    terms = tokenize(text)
    if not terms:
        return []
    toolbox.ensure_search_index()
    filter_sql, parameters = _filter_sql(filters)
    rows: list[tuple[Any, ...]] = toolbox.connection.execute(
        _SEARCH_SQL.format(filters=filter_sql),
        [*parameters, terms, k],
    ).fetchall()
    return [
        SimilarCase(
            id=str(row[0]),
            make=str(row[1]),
            model=str(row[2]),
            year=int(row[3]),
            group=str(row[4] or ""),
            excerpt=_excerpt(str(row[5] or "")),
            score=float(row[6]),
        )
        for row in rows
    ]
