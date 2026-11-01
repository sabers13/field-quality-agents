"""The Q5 tool seam over Q2's real tools, with evidence capture for a run.

``RecordingTools`` is what the batch pipeline passes to the desk graph: it
delegates every call to the DuckDB tools and keeps the exact results per case,
so the run can write ``evidence.json`` for the dashboard and
``tool_outputs.json`` for a faithful live replay. ``ReplayTools`` serves those
recorded results back to the graph without opening DuckDB.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, cast

from field_quality_agents.agents.tools import (
    CaseFilters as GraphCaseFilters,
)
from field_quality_agents.agents.tools import (
    QuoteVerification as GraphQuoteVerification,
)
from field_quality_agents.agents.tools import (
    SimilarCase as GraphSimilarCase,
)
from field_quality_agents.contracts import Clue
from field_quality_agents.tools import cluster
from field_quality_agents.tools.db import Toolbox
from field_quality_agents.tools.lookup import (
    investigations_for as lookup_investigations,
)
from field_quality_agents.tools.lookup import (
    recalls_for as lookup_recalls,
)
from field_quality_agents.tools.models import CaseFilters as ToolCaseFilters
from field_quality_agents.tools.models import ClusterStats
from field_quality_agents.tools.quotes import verify_quotes as check_quotes
from field_quality_agents.tools.rules import load_rules, match_rules
from field_quality_agents.tools.rules import rulebook as match_rulebook
from field_quality_agents.tools.search import similar_cases as search_similar

__all__ = [
    "CaseToolOutputs",
    "RecordingTools",
    "ReplayTools",
    "ToolboxIssueTools",
    "outputs_as_json",
    "rulebook_path",
]


def rulebook_path(explicit: str | Path | None = None) -> Path:
    """Find ``config/rulebook.toml`` from the checkout."""

    if explicit is not None:
        return Path(explicit)
    candidates = (
        Path.cwd() / "config" / "rulebook.toml",
        Path(__file__).resolve().parents[3] / "config" / "rulebook.toml",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def _graph_filter(filters: GraphCaseFilters | None) -> ToolCaseFilters | None:
    if filters is None:
        return None
    return ToolCaseFilters(
        make=filters.make,
        model=filters.model,
        year=filters.year,
        group=filters.group,
        safety_relevant=filters.safety_relevant,
    )


def _graph_similar(item: Any) -> GraphSimilarCase:
    return GraphSimilarCase(
        id=str(item.id),
        score=float(item.score),
        make=str(item.make),
        model=str(item.model),
        year=int(item.year),
        group=str(item.group),
        excerpt=str(item.excerpt),
    )


def _graph_quote(item: Any) -> GraphQuoteVerification:
    return GraphQuoteVerification(quote=str(item.quote), verified=bool(item.verified))


def _similar_dict(item: GraphSimilarCase) -> dict[str, object]:
    return {
        "id": item.id,
        "score": item.score,
        "make": item.make,
        "model": item.model,
        "year": item.year,
        "group": item.group,
        "excerpt": item.excerpt,
    }


@dataclass
class CaseToolOutputs:
    """The tool results the graph saw for one case."""

    similar_cases: list[dict[str, object]]
    recalls: list[dict[str, object]]
    investigations: list[dict[str, object]]

    def as_dict(self) -> dict[str, object]:
        return {
            "similar_cases": list(self.similar_cases),
            "recalls": list(self.recalls),
            "investigations": list(self.investigations),
        }

    def evidence(self) -> dict[str, object]:
        return {
            "similar_cases": list(self.similar_cases),
            "recalls": [
                _ref(row) for row in self.recalls if isinstance(row.get("id"), str)
            ],
            "investigations": [
                _ref(row) for row in self.investigations if isinstance(row.get("id"), str)
            ],
        }


def _ref(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "id": str(row.get("id", "")),
        "summary": str(row.get("summary", "")),
        "open_date": row.get("open_date"),
        "match": bool(row.get("match", True)),
    }


class RecordingTools:
    """Delegate to Q2's tools and remember each case's evidence."""

    def __init__(self, toolbox: Toolbox) -> None:
        self._toolbox = toolbox
        self.current_case_id: str | None = None
        self._outputs: dict[str, CaseToolOutputs] = {}

    def _outputs_for(self, case_id: str) -> CaseToolOutputs:
        return self._outputs.setdefault(
            case_id,
            CaseToolOutputs(similar_cases=[], recalls=[], investigations=[]),
        )

    def similar_cases(
        self,
        text: str,
        filters: GraphCaseFilters | None = None,
        k: int = 10,
    ) -> list[GraphSimilarCase]:
        results = [
            _graph_similar(item)
            for item in search_similar(self._toolbox, text, _graph_filter(filters), k)
        ]
        if self.current_case_id is not None:
            self._outputs_for(self.current_case_id).similar_cases = [
                _similar_dict(item) for item in results
            ]
        return results

    def recalls_for(
        self, make: str, model: str, year: int, group: str
    ) -> list[dict[str, object]]:
        rows = lookup_recalls(self._toolbox, make, model, year, group)
        if self.current_case_id is not None:
            self._outputs_for(self.current_case_id).recalls = [
                dict(row) for row in rows
            ]
        return rows

    def investigations_for(
        self, make: str, model: str, year: int, group: str
    ) -> list[dict[str, object]]:
        rows = lookup_investigations(self._toolbox, make, model, year, group)
        if self.current_case_id is not None:
            self._outputs_for(self.current_case_id).investigations = [
                dict(row) for row in rows
            ]
        return rows

    def rulebook(self, conditions: Sequence[str]) -> list[dict[str, object]]:
        return match_rulebook(self._toolbox.rulebook_path, conditions)

    def verify_quotes(
        self, text: str, quotes: Sequence[Clue]
    ) -> list[GraphQuoteVerification]:
        return [_graph_quote(item) for item in check_quotes(text, quotes)]

    def outputs(self, case_id: str) -> CaseToolOutputs:
        return self._outputs.get(case_id) or CaseToolOutputs([], [], [])

    def all_outputs(self) -> dict[str, object]:
        return {
            case_id: outputs.as_dict()
            for case_id, outputs in sorted(self._outputs.items())
        }


class ToolboxIssueTools:
    """The issue agent's fleet tools over one open :class:`Toolbox`."""

    def __init__(self, toolbox: Toolbox) -> None:
        self._toolbox = toolbox

    def cluster_stats(
        self,
        make: str,
        model: str,
        year: int,
        group: str,
        until_date: date,
    ) -> ClusterStats:
        return cluster.cluster_stats(
            self._toolbox, make, model, year, group, until_date
        )

    def recalls_for(
        self, make: str, model: str, year: int, group: str
    ) -> list[dict[str, object]]:
        return lookup_recalls(self._toolbox, make, model, year, group)

    def investigations_for(
        self, make: str, model: str, year: int, group: str
    ) -> list[dict[str, object]]:
        return lookup_investigations(self._toolbox, make, model, year, group)


class ReplayTools:
    """Serve recorded tool results to a live replay of the desk graph."""

    def __init__(
        self,
        outputs: Mapping[str, object],
        *,
        rulebook: str | Path | None = None,
    ) -> None:
        self._outputs = outputs
        self.current_case_id: str | None = None
        self._rules = load_rules(rulebook_path(rulebook))

    def _block(self, key: str) -> list[dict[str, object]]:
        if self.current_case_id is None:
            return []
        case = self._outputs.get(self.current_case_id)
        if not isinstance(case, Mapping):
            return []
        rows = cast(Mapping[str, object], case).get(key)
        if not isinstance(rows, list):
            return []
        return [cast(dict[str, object], row) for row in rows if isinstance(row, dict)]

    def similar_cases(
        self,
        text: str,
        filters: GraphCaseFilters | None = None,
        k: int = 10,
    ) -> list[GraphSimilarCase]:
        del text, filters
        rows = self._block("similar_cases")[:k]
        return [
            GraphSimilarCase(
                id=str(row.get("id", "")),
                score=float(cast(float, row.get("score", 0.0))),
                make=str(row.get("make", "")),
                model=str(row.get("model", "")),
                year=int(cast(int, row.get("year", 0))),
                group=str(row.get("group", "")),
                excerpt=str(row.get("excerpt", "")),
            )
            for row in rows
        ]

    def recalls_for(
        self, make: str, model: str, year: int, group: str
    ) -> list[dict[str, object]]:
        del make, model, year, group
        return [dict(row) for row in self._block("recalls")]

    def investigations_for(
        self, make: str, model: str, year: int, group: str
    ) -> list[dict[str, object]]:
        del make, model, year, group
        return [dict(row) for row in self._block("investigations")]

    def rulebook(self, conditions: Sequence[str]) -> list[dict[str, object]]:
        return match_rules(self._rules, conditions)

    def verify_quotes(
        self, text: str, quotes: Sequence[Clue]
    ) -> list[GraphQuoteVerification]:
        return [_graph_quote(item) for item in check_quotes(text, quotes)]


def outputs_as_json(recording: RecordingTools) -> dict[str, object]:
    """Serialise every captured tool result for ``tool_outputs.json``."""

    return recording.all_outputs()
