"""Analysis agent: gather evidence with the tools and propose a test."""

from __future__ import annotations

import json

from field_quality_agents.agents.model import (
    AgentModel,
    ModelOutputError,
    as_bool,
    as_clues,
    as_text,
    as_text_list,
    parse_json_object,
)
from field_quality_agents.agents.prompts import load_prompt
from field_quality_agents.agents.state import (
    PROMPT_VERSION,
    DeskState,
    Node,
    StepWriter,
    utcnow,
)
from field_quality_agents.agents.tools import CaseFilters, ToolRegistry, tool_output
from field_quality_agents.contracts import (
    Case,
    CaseStatus,
    Citation,
    Clue,
    Extraction,
    Proposal,
    ProposalKind,
    SourceType,
    TargetedTest,
)


def _rule_name(rules: list[dict[str, object]]) -> str:
    for rule in rules:
        for key in ("test", "name"):
            value = rule.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return "Targeted load test"


def _rule_conditions(rules: list[dict[str, object]]) -> tuple[str, ...]:
    conditions: list[str] = []
    for rule in rules:
        value = rule.get("conditions")
        if isinstance(value, list):
            conditions.extend(
                item.strip() for item in value if isinstance(item, str) and item.strip()
            )
    return tuple(dict.fromkeys(conditions))


def _citations(case: Case, clues: tuple[Clue, ...]) -> tuple[Citation, ...]:
    return tuple(
        Citation(
            source_type=SourceType.CASE,
            source_id=case.id,
            quote=clue.quote,
            verified=True,
        )
        for clue in clues
    )


def _info_request(case: Case, reason: str) -> Proposal:
    return Proposal(
        case_id=case.id,
        kind=ProposalKind.REQUEST_INFO,
        summary="Information request: the analysis needs a readable report",
        rationale=reason,
        requested_info=("Re-read the report and confirm the symptom and conditions",),
        created_at=utcnow(),
    )


def make_analysis_node(model: AgentModel, tools: ToolRegistry) -> Node:
    """Build the analysis node around a model and the tool seam."""

    prompt = load_prompt("analysis")

    def analysis(state: DeskState) -> dict[str, object]:
        case = state["case"]
        extraction = state["extraction"]
        writer = StepWriter(state)

        similar = tools.similar_cases(
            case.narrative,
            CaseFilters(
                make=case.make,
                model=case.model,
                year=case.year,
                group=extraction.group,
            ),
            5,
        )
        writer.add(
            agent="analysis",
            action="search_similar_cases",
            reason=f"{len(similar)} similar case(s) in the knowledge base",
            tool="similar_cases",
            tool_input={"text": case.narrative[:500], "k": 5},
            tool_output=tool_output(similar),
        )

        recalls = tools.recalls_for(case.make, case.model, case.year, extraction.group)
        writer.add(
            agent="analysis",
            action="lookup_recalls",
            reason=f"{len(recalls)} recall(s) for the same vehicle and group",
            tool="recalls_for",
            tool_input={
                "make": case.make,
                "model": case.model,
                "year": case.year,
                "group": extraction.group,
            },
            tool_output=tool_output(recalls),
        )

        investigations = tools.investigations_for(
            case.make, case.model, case.year, extraction.group
        )
        writer.add(
            agent="analysis",
            action="lookup_investigations",
            reason=f"{len(investigations)} investigation(s) for the same vehicle and group",
            tool="investigations_for",
            tool_input={
                "make": case.make,
                "model": case.model,
                "year": case.year,
                "group": extraction.group,
            },
            tool_output=tool_output(investigations),
        )

        rules = tools.rulebook(extraction.conditions)
        writer.add(
            agent="analysis",
            action="read_rulebook",
            reason=f"{len(rules)} targeted-test rule(s) matched the reported conditions",
            tool="rulebook",
            tool_input={"conditions": list(extraction.conditions)},
            tool_output=tool_output(rules),
        )

        messages = (
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "case": case.model_dump(mode="json"),
                        "extraction": extraction.model_dump(mode="json"),
                        "similar_cases": tool_output(similar),
                        "recalls": tool_output(recalls),
                        "investigations": tool_output(investigations),
                        "rulebook": tool_output(rules),
                    },
                    sort_keys=True,
                ),
            },
        )

        payload: dict[str, object] = {}
        tokens = 0
        readable = True
        try:
            turn = model.complete(
                agent="analysis",
                prompt_version=PROMPT_VERSION,
                prompt=prompt,
                messages=messages,
            )
            tokens = turn.tokens
            payload = parse_json_object(turn.text)
            writer.add(
                agent="analysis",
                action="propose",
                reason=as_text(payload, "rationale", "analysed the evidence"),
                tokens=turn.tokens,
                cost_usd=turn.cost_usd,
                duration_ms=turn.duration_ms,
            )
        except ModelOutputError:
            readable = False
            writer.add(
                agent="analysis",
                action="unreadable_model_output",
                reason="model answer was not a JSON object; asking the engineer",
            )

        if not readable:
            updated = case.model_copy(update={"status": CaseStatus.ANALYSIS})
            return writer.updates(
                case=updated,
                proposal=_info_request(case, "The analysis could not read the model answer."),
                tokens=state.get("tokens", 0) + tokens,
            )

        clues = as_clues(payload)
        checks = tools.verify_quotes(case.narrative, clues)
        verified: list[Clue] = []
        dropped = 0
        for index, clue in enumerate(clues):
            check = checks[index] if index < len(checks) else None
            if check is not None and check.verified:
                verified.append(clue)
            else:
                dropped += 1
        verified_clues = tuple(verified)

        writer.add(
            agent="analysis",
            action="verify_quotes",
            reason=f"{len(verified_clues)} verified, {dropped} dropped",
            tool="verify_quotes",
            tool_input={"quotes": [clue.quote for clue in clues]},
            tool_output={
                "checked": len(clues),
                "verified": len(verified_clues),
                "dropped": dropped,
            },
        )
        if dropped:
            writer.add(
                agent="analysis",
                action="drop_unverified_quotes",
                reason=f"{dropped} clue(s) failed quote verification and are not evidence",
            )

        conditions = as_text_list(payload, "conditions") or extraction.conditions
        targeted = as_bool(payload, "targeted") or bool(rules)
        safety = as_bool(payload, "safety_relevant")
        evidence = _citations(case, verified_clues)

        if safety:
            kind = ProposalKind.SAFETY_PRIORITY
            summary = "Safety-relevant: send to an engineer before any test is booked"
            targeted_test = None
        elif targeted:
            kind = ProposalKind.TARGETED_LOAD_TEST
            name = as_text(payload, "test_name") or _rule_name(rules)
            rule_conditions = _rule_conditions(rules)
            targeted_test = TargetedTest(
                name=name,
                conditions=tuple(dict.fromkeys((*conditions, *rule_conditions))),
                reason=as_text(payload, "rationale", "conditions match a targeted test rule"),
            )
            summary = as_text(payload, "summary") or f"{name} for {case.component}"
        else:
            kind = ProposalKind.STANDARD_TEST
            targeted_test = None
            summary = as_text(payload, "summary") or f"Standard test for {case.component}"

        proposal = Proposal(
            case_id=case.id,
            kind=kind,
            summary=summary,
            rationale=as_text(payload, "rationale"),
            targeted_test=targeted_test,
            evidence=evidence,
            created_at=utcnow(),
        )

        updated_extraction = Extraction(
            case_id=case.id,
            group=as_text(payload, "group") or extraction.group,
            summary=as_text(payload, "summary") or extraction.summary,
            symptoms=as_text_list(payload, "symptoms") or extraction.symptoms,
            conditions=conditions,
            fault_codes=as_text_list(payload, "fault_codes") or extraction.fault_codes,
            clues=verified_clues,
            safety_relevant=safety or extraction.safety_relevant,
        )
        updated_case = case.model_copy(
            update={
                "status": CaseStatus.ANALYSIS,
                "safety_relevant": case.safety_relevant or safety,
            }
        )
        return writer.updates(
            case=updated_case,
            extraction=updated_extraction,
            proposal=proposal,
            safety_relevant=state.get("safety_relevant", False) or safety,
            tokens=state.get("tokens", 0) + tokens,
        )

    return analysis
