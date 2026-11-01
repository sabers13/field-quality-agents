"""Intake agent: normalise the report, check completeness, hint duplicates."""

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
    Extraction,
    Proposal,
    ProposalKind,
)


def _info_request(case: Case, missing: tuple[str, ...]) -> Proposal:
    return Proposal(
        case_id=case.id,
        kind=ProposalKind.REQUEST_INFO,
        summary="Information request: " + ", ".join(missing),
        rationale="The report is missing information the analysis needs.",
        requested_info=missing,
        created_at=utcnow(),
    )


def make_intake_node(model: AgentModel, tools: ToolRegistry) -> Node:
    """Build the intake node around a model and the tool seam."""

    prompt = load_prompt("intake")

    def intake(state: DeskState) -> dict[str, object]:
        case = state["case"]
        writer = StepWriter(state)
        messages = (
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(case.model_dump(mode="json"), sort_keys=True)},
        )

        payload: dict[str, object] = {}
        tokens = 0
        readable = True
        try:
            turn = model.complete(
                agent="intake",
                prompt_version=PROMPT_VERSION,
                prompt=prompt,
                messages=messages,
            )
            tokens = turn.tokens
            payload = parse_json_object(turn.text)
            writer.add(
                agent="intake",
                action="extract",
                reason=as_text(payload, "summary", "normalised the report"),
                tokens=turn.tokens,
                cost_usd=turn.cost_usd,
                duration_ms=turn.duration_ms,
            )
        except ModelOutputError:
            readable = False
            writer.add(
                agent="intake",
                action="unreadable_model_output",
                reason="model answer was not a JSON object; asking the engineer",
            )

        extraction = Extraction(
            case_id=case.id,
            group=as_text(payload, "group") or case.group or "unclear",
            summary=as_text(payload, "summary"),
            symptoms=as_text_list(payload, "symptoms"),
            conditions=as_text_list(payload, "conditions"),
            fault_codes=as_text_list(payload, "fault_codes"),
            clues=as_clues(payload),
            safety_relevant=as_bool(payload, "safety_relevant"),
        )

        duplicates = tools.similar_cases(
            case.narrative,
            CaseFilters(
                make=case.make,
                model=case.model,
                year=case.year,
                group=case.group,
            ),
            3,
        )
        writer.add(
            agent="intake",
            action="check_duplicates",
            reason=f"{len(duplicates)} similar case(s) within the same vehicle",
            tool="similar_cases",
            tool_input={"k": 3, "make": case.make, "model": case.model, "year": case.year},
            tool_output=tool_output(duplicates),
        )

        missing = as_text_list(payload, "missing_info")
        proposal: Proposal | None = None
        if not readable or missing:
            reason_text = "unreadable model output" if not readable else "report incomplete"
            proposal = _info_request(case, missing or ("a readable report",))
            writer.add(
                agent="intake",
                action="draft_info_request",
                reason=reason_text,
            )

        updated = case.model_copy(
            update={
                "status": CaseStatus.INTAKE,
                "safety_relevant": case.safety_relevant or extraction.safety_relevant,
            }
        )
        return writer.updates(
            case=updated,
            extraction=extraction,
            proposal=proposal,
            safety_relevant=case.safety_relevant or extraction.safety_relevant,
            tokens=state.get("tokens", 0) + tokens,
        )

    return intake
