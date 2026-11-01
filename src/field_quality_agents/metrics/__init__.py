"""Pure PLAN §7 metrics, shared by the linear and agentic pipelines.

Every function is deterministic: no I/O, no model call, and no randomness
except an optional seeded ``random.Random`` for the macro-F1 bootstrap and the
issue base rate. Both pipelines feed the same functions, so a before/after
comparison is apples to apples.
"""

from __future__ import annotations

from field_quality_agents.metrics.classification import group_coverage, macro_f1
from field_quality_agents.metrics.compare import Comparison, ComparisonRow, compare
from field_quality_agents.metrics.estimates import (
    DEFAULT_SEED,
    estimate,
    mean,
    percentile,
    wilson_interval,
)
from field_quality_agents.metrics.evidence import (
    RecallLink,
    SourceIndex,
    citation_validity,
    quote_grounding,
    recall_link_match_rate,
    targeted_test_share,
    targeted_test_with_quote_share,
)
from field_quality_agents.metrics.issues import Event, issue_detection
from field_quality_agents.metrics.safety import safety_scores
from field_quality_agents.metrics.workload import workload

__all__ = [
    "DEFAULT_SEED",
    "Comparison",
    "ComparisonRow",
    "Event",
    "RecallLink",
    "SourceIndex",
    "citation_validity",
    "compare",
    "estimate",
    "group_coverage",
    "issue_detection",
    "macro_f1",
    "mean",
    "percentile",
    "quote_grounding",
    "recall_link_match_rate",
    "safety_scores",
    "targeted_test_share",
    "targeted_test_with_quote_share",
    "wilson_interval",
    "workload",
]
