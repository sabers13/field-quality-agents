"""Fakes and helpers for the agent-graph tests.

The model and tools are injected exactly as Q4 and Q2 will inject their real
implementations, so no test touches the network or the committed data.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date

from field_quality_agents.agents.graph import DeskGraph, build_desk_graph, run_case
from field_quality_agents.agents.model import ModelTurn
from field_quality_agents.agents.simulated_engineer import decide
from field_quality_agents.agents.state import CaseRun
from field_quality_agents.agents.tools import (
    CaseFilters,
    QuoteVerification,
    SimilarCase,
)
from field_quality_agents.contracts import Case, Clue


def make_case(**overrides: object) -> Case:
    data: dict[str, object] = {
        "id": "CASE-1",
        "received_at": date(2025, 3, 4),
        "make": "Make A",
        "model": "Model B",
        "year": 2022,
        "component": "Instrument cluster display",
        "group": "display",
        "narrative": (
            "The display goes blank when the cabin is cold and the ignition is "
            "switched on. It returns after the cabin warms up."
        ),
        "safety_relevant": False,
    }
    data.update(overrides)
    return Case.model_validate(data)


class ScriptedModel:
    """Return one scripted answer per agent, in call order."""

    def __init__(self, turns: Mapping[str, Sequence[ModelTurn | str]]) -> None:
        self._turns = {agent: list(items) for agent, items in turns.items()}
        self.calls: list[dict[str, object]] = []

    def complete(
        self,
        *,
        agent: str,
        prompt_version: str,
        prompt: str,
        messages: Sequence[Mapping[str, object]],
        tools: Sequence[Mapping[str, object]] = (),
    ) -> ModelTurn:
        self.calls.append(
            {
                "agent": agent,
                "prompt_version": prompt_version,
                "messages": tuple(messages),
                "tools": tuple(tools),
            }
        )
        queue = self._turns.get(agent)
        if not queue:
            raise AssertionError(f"no scripted answer left for agent {agent!r}")
        item = queue.pop(0)
        return item if isinstance(item, ModelTurn) else ModelTurn(text=item)


def _normalise(text: str) -> str:
    return " ".join(text.split()).lower()


@dataclass
class FakeTools:
    """A small in-memory implementation of the Q2 tool signatures."""

    similar: list[SimilarCase] = field(default_factory=list)
    recalls: list[dict[str, object]] = field(default_factory=list)
    investigations: list[dict[str, object]] = field(default_factory=list)
    rules: list[dict[str, object]] = field(default_factory=list)
    calls: list[tuple[str, dict[str, object]]] = field(default_factory=list)

    def similar_cases(
        self,
        text: str,
        filters: CaseFilters | None = None,
        k: int = 10,
    ) -> list[SimilarCase]:
        self.calls.append(("similar_cases", {"text": text, "k": k}))
        return self.similar[:k]

    def recalls_for(
        self, make: str, model: str, year: int, group: str
    ) -> list[dict[str, object]]:
        self.calls.append(
            ("recalls_for", {"make": make, "model": model, "year": year, "group": group})
        )
        return list(self.recalls)

    def investigations_for(
        self, make: str, model: str, year: int, group: str
    ) -> list[dict[str, object]]:
        self.calls.append(
            (
                "investigations_for",
                {"make": make, "model": model, "year": year, "group": group},
            )
        )
        return list(self.investigations)

    def rulebook(self, conditions: Sequence[str]) -> list[dict[str, object]]:
        self.calls.append(("rulebook", {"conditions": list(conditions)}))
        wanted = set(conditions)
        matched: list[dict[str, object]] = []
        for rule in self.rules:
            rule_conditions = rule.get("conditions")
            if isinstance(rule_conditions, list) and wanted.intersection(rule_conditions):
                matched.append(rule)
        return matched

    def verify_quotes(self, text: str, quotes: Sequence[Clue]) -> list[QuoteVerification]:
        self.calls.append(("verify_quotes", {"quotes": len(quotes)}))
        body = _normalise(text)
        return [
            QuoteVerification(quote=clue.quote, verified=_normalise(clue.quote) in body)
            for clue in quotes
        ]


def intake_payload(
    *,
    summary: str = "Display blanks in the cold",
    conditions: Sequence[str] = ("cold",),
    quotes: Sequence[str] = ("goes blank when the cabin is cold",),
    missing: Sequence[str] = (),
    safety: bool = False,
    tokens: int = 120,
) -> ModelTurn:
    payload = {
        "summary": summary,
        "group": "display",
        "symptoms": ["display blank"],
        "conditions": list(conditions),
        "fault_codes": [],
        "safety_relevant": safety,
        "missing_info": list(missing),
        "clues": [{"kind": "symptom", "quote": quote} for quote in quotes],
    }
    return ModelTurn(text=json.dumps(payload), tokens=tokens)


def analysis_payload(
    *,
    targeted: bool = True,
    quotes: Sequence[str] = (
        "goes blank when the cabin is cold",
        "returns after the cabin warms up",
    ),
    test_name: str = "Low-temperature cycling",
    safety: bool = False,
) -> ModelTurn:
    payload = {
        "summary": "Low-temperature cycling is the right next test",
        "rationale": "the display blanks only in the cold",
        "group": "display",
        "symptoms": ["display blank"],
        "conditions": ["cold"],
        "fault_codes": [],
        "safety_relevant": safety,
        "targeted": targeted,
        "test_name": test_name,
        "clues": [{"kind": "condition", "quote": quote} for quote in quotes],
    }
    return ModelTurn(text=json.dumps(payload), tokens=240)


def build_graph(
    *,
    intake: ModelTurn | None = None,
    analysis: ModelTurn | None = None,
    tools: FakeTools | None = None,
) -> tuple[DeskGraph, ScriptedModel, FakeTools]:
    turns: dict[str, list[ModelTurn | str]] = {}
    if intake is not None:
        turns["intake"] = [intake]
    if analysis is not None:
        turns["analysis"] = [analysis]
    model = ScriptedModel(turns)
    registry = tools if tools is not None else FakeTools(
        rules=[{"conditions": ["cold"], "test": "Low-temperature cycling"}]
    )
    return build_desk_graph(tools=registry, model=model), model, registry


def run_desk(
    case: Case,
    *,
    intake: ModelTurn | None = None,
    analysis: ModelTurn | None = None,
    tools: FakeTools | None = None,
    engineer: object = None,
) -> tuple[CaseRun, ScriptedModel, FakeTools]:
    graph, model, registry = build_graph(intake=intake, analysis=analysis, tools=tools)
    decider = decide if engineer is None else engineer
    run = run_case(case, graph, engineer=decider)  # type: ignore[arg-type]
    return run, model, registry


__all__ = [
    "CaseFilters",
    "FakeTools",
    "ScriptedModel",
    "analysis_payload",
    "build_graph",
    "intake_payload",
    "make_case",
    "run_desk",
]
