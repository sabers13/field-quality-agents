"""What a case looks like to the model.

PLAN §7 scores the component group and the safety flag against NHTSA's own
labels, so both columns are *evaluation targets*. A model that receives them
can copy them, and the metric then measures the answer key rather than the
desk. :func:`model_case_payload` is the single place that decides what travels
into a request, so the labels leave the payload in one edit.

The desk still keeps the labels on its own ``Case`` objects: the supervisor
routing in PLAN §4 and the fleet clustering use them as operational inputs.
Only the request payload is scrubbed.
"""

from __future__ import annotations

from typing import Any

from field_quality_agents.contracts import Case

__all__ = ["EVALUATION_FIELDS", "MODEL_INPUT_CLEAN", "MODEL_INPUT_LEGACY", "model_case_payload"]

#: The Case columns PLAN §7 scores against NHTSA's coding.
EVALUATION_FIELDS: tuple[str, ...] = ("group", "safety_relevant")

#: Recorded requests that never carried the evaluation labels.
MODEL_INPUT_CLEAN = "clean"

#: The Q9 recordings were made before the scrub existed. Replaying them needs
#: the historical payload; the run manifest and the metrics record that the
#: label-dependent numbers are therefore withheld.
MODEL_INPUT_LEGACY = "legacy-evaluation-labels"


def model_case_payload(
    case: Case,
    *,
    include_evaluation_labels: bool = False,
) -> dict[str, Any]:
    """Return the case as the model may see it.

    With ``include_evaluation_labels`` false — the default and the only policy a
    live or record run may use — the PLAN §7 targets are removed. The flag
    exists solely to replay the frozen pre-fix recordings, and the CLI refuses
    it outside replay mode.
    """

    payload: dict[str, Any] = case.model_dump(mode="json")
    if not include_evaluation_labels:
        for field in EVALUATION_FIELDS:
            payload.pop(field, None)
    return payload
