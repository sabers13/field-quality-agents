"""The linear baseline: keyword rules, the fixed pipeline and references."""

from __future__ import annotations

from field_quality_agents.baseline.keywords import (
    DEFAULT_KEYWORDS_PATH,
    KeywordGroup,
    KeywordMatch,
    KeywordRules,
    SafetyMatch,
    load_keywords,
    normalise_tokens,
    safety_flag,
    sort_component,
)
from field_quality_agents.baseline.pipeline import (
    BaselineDecision,
    baseline_runs,
    run_linear,
)
from field_quality_agents.baseline.runner import BaselineReport, load_cases, run_baseline
from field_quality_agents.baseline.tfidf import (
    TfidfReference,
    fit_tfidf_logreg,
    run_tfidf_logreg,
)

__all__ = [
    "DEFAULT_KEYWORDS_PATH",
    "BaselineDecision",
    "BaselineReport",
    "KeywordGroup",
    "KeywordMatch",
    "KeywordRules",
    "SafetyMatch",
    "TfidfReference",
    "baseline_runs",
    "fit_tfidf_logreg",
    "load_cases",
    "load_keywords",
    "normalise_tokens",
    "run_baseline",
    "run_linear",
    "run_tfidf_logreg",
    "safety_flag",
    "sort_component",
]
