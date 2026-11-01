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
from field_quality_agents.agents.payload import model_case_payload
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
    Clue,
    Extraction,
    Proposal,
    ProposalKind,
)
from field_quality_agents.llm.errors import BadAnswerError

#: Facts the desk cannot analyse without. The model's ``missing_info`` list is
#: advisory for the rest: NHTSA reports often omit mileage, and the desk always
#: has the received date, so neither may stop a case at intake (Q9 smoke run
#: showed 19 of 20 cases blocked on mileage/date before this filter).
ESSENTIAL_INFO = frozenset({"component", "symptom"})


def _info_request(case: Case, missing: tuple[str, ...]) -> Proposal:
    return Proposal(
        case_id=case.id,
        kind=ProposalKind.REQUEST_INFO,
        summary="Information request: " + ", ".join(missing),
        rationale="The report is missing information the analysis needs.",
        requested_info=missing,
        created_at=utcnow(),
    )


def _intake_clues(
    *,
    case: Case,
    tools: ToolRegistry,
    writer: StepWriter,
    payload: dict[str, object],
    verify: bool,
) -> tuple[Clue, ...]:
    """Return the clues intake may keep.

    PLAN §4 makes dropping an unverified quote a hard rule in code. Intake
    extracts clues too, and a safety or information-request case never reaches
    analysis, so the check has to happen here as well or the clue is never
    checked at all. The frozen Q9 replay keeps the recorded output unchanged.
    """

    clues = as_clues(payload)
    if not verify:
        return clues

    checks = tools.verify_quotes(case.narrative, clues)
    verified = [
        clue
        for index, clue in enumerate(clues)
        if index < len(checks) and checks[index].verified
    ]
    dropped = len(clues) - len(verified)
    writer.add(
        agent="intake",
        action="verify_quotes",
        reason=f"{len(verified)} verified, {dropped} dropped",
        tool="verify_quotes",
        tool_input={"quotes": [clue.quote for clue in clues]},
        tool_output={
            "checked": len(clues),
            "verified": len(verified),
            "dropped": dropped,
        },
    )
    if dropped:
        writer.add(
            agent="intake",
            action="drop_unverified_quotes",
            reason=f"{dropped} clue(s) failed quote verification and are not kept",
            counts=False,
        )
    return tuple(verified)


def make_intake_node(
    model: AgentModel,
    tools: ToolRegistry,
    *,
    include_evaluation_labels: bool = False,
) -> Node:
    """Build the intake node around a model and the tool seam.

    ``include_evaluation_labels`` reproduces the frozen Q9 requests during a
    replay of those recordings. A live or record run never sets it: the model
    must not see PLAN §7's targets.
    """

    prompt = load_prompt("intake")

    def intake(state: DeskState) -> dict[str, object]:
        case = state["case"]
        writer = StepWriter(state)
        messages = (
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps(
                    model_case_payload(
                        case,
                        include_evaluation_labels=include_evaluation_labels,
                    ),
                    sort_keys=True,
                ),
            },
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
        except (ModelOutputError, BadAnswerError):
            readable = False
            writer.add(
                agent="intake",
                action="unreadable_model_output",
                reason="model answer was unreadable; asking the engineer",
            )

        extraction_group: str | None = as_text(payload, "group")
        if not extraction_group and include_evaluation_labels:
            # The recorded pipeline fell back to the case's own group; keep that
            # only for the frozen replay, never for a new run.
            extraction_group = case.group
        extraction = Extraction(
            case_id=case.id,
            group=extraction_group or "unclear",
            summary=as_text(payload, "summary"),
            symptoms=as_text_list(payload, "symptoms"),
            conditions=as_text_list(payload, "conditions"),
            fault_codes=as_text_list(payload, "fault_codes"),
            clues=_intake_clues(
                case=case,
                tools=tools,
                writer=writer,
                payload=payload,
                verify=not include_evaluation_labels,
            ),
            safety_relevant=as_bool(payload, "safety_relevant"),
        )

        predicted_safety = extraction.safety_relevant
        if include_evaluation_labels:
            # The recorded pipeline ORed NHTSA's flag into the prediction. A new
            # run scores the desk's own flag, so the truth stays out of it.
            predicted_safety = case.safety_relevant or extraction.safety_relevant

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
        blocking = tuple(item for item in missing if item in ESSENTIAL_INFO)
        proposal: Proposal | None = None
        if not readable or blocking:
            if readable:
                reason_text = "missing essential information: " + ", ".join(blocking)
            else:
                reason_text = "unreadable model output"
            proposal = _info_request(case, blocking or ("a readable report",))
            writer.add(
                agent="intake",
                action="draft_info_request",
                reason=reason_text,
            )
        elif missing:
            writer.add(
                agent="intake",
                action="note_missing_info",
                reason="the report omits " + ", ".join(missing) + "; analysis can proceed",
                counts=False,
            )

        updated = case.model_copy(
            update={
                "status": CaseStatus.INTAKE,
                "safety_relevant": predicted_safety,
            }
        )
        return writer.updates(
            case=updated,
            extraction=extraction,
            proposal=proposal,
            safety_relevant=predicted_safety,
            tokens=state.get("tokens", 0) + tokens,
        )

    return intake
