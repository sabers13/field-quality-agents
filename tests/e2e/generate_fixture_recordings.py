"""Regenerate the committed fixture recordings for Q8's replay run.

This is a maintenance script, not a test. It runs the real pipeline with a
deterministic scripted model and stores every answer in the same record/replay
store the pipeline reads, keyed exactly as ``LangChainChatModel`` keys a live
turn. Commit the resulting ``tests/fixtures/recordings/`` files; ``make all``
replays them without a model or a network.

Run from the repository root:

    uv run python tests/e2e/generate_fixture_recordings.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from field_quality_agents.agents.model import AgentModel, ModelTurn  # noqa: E402
from field_quality_agents.contracts import RunMode  # noqa: E402
from field_quality_agents.llm.models import ChatResponse, Usage  # noqa: E402
from field_quality_agents.llm.prices import DEFAULT_MODEL  # noqa: E402
from field_quality_agents.llm.recorder import RecordReplayStore  # noqa: E402
from field_quality_agents.run.data import open_source  # noqa: E402
from field_quality_agents.run.pipeline import execute_run  # noqa: E402

RECORDINGS = ROOT / "tests" / "fixtures" / "recordings"
FIXTURE_SQL = ROOT / "tests" / "fixtures" / "e2e" / "replay_2025.sql"
PROMPT_VERSION = "p1"
TOKENS = 180
COST_USD = 0.000108
LATENCY_MS = 12


def _case_from(messages: Sequence[Mapping[str, object]]) -> dict[str, object]:
    for message in messages:
        content = message.get("content")
        if not isinstance(content, str) or not content.strip().startswith("{"):
            continue
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("case"), dict):
            return payload["case"]  # analysis prompt
        if isinstance(payload, dict) and "narrative" in payload:
            return payload  # intake prompt
    raise AssertionError("no case object in the prompt messages")


def _conditions(narrative: str) -> list[str]:
    text = narrative.lower()
    if "cold" in text:
        return ["cold", "damp"]
    if "charging" in text or "charge" in text:
        return ["charging", "heat"]
    if "intermittent" in text:
        return ["intermittent"]
    if "vibration" in text:
        return ["vibration"]
    return []


def _quote(narrative: str) -> str:
    first = narrative.split(",")[0].strip()
    return first or narrative.strip()


def _test_name(conditions: Sequence[str]) -> str:
    if "cold" in conditions:
        return "Low-temperature cycling test"
    if "charging" in conditions:
        return "Electrical load test"
    if "vibration" in conditions:
        return "Vibration test"
    return "Long-run power cycling test"


class FixtureModel:
    """A deterministic answer for each agent; it never calls a network."""

    def complete(
        self,
        *,
        agent: str,
        prompt_version: str,
        prompt: str,
        messages: Sequence[Mapping[str, object]],
        tools: Sequence[Mapping[str, object]] = (),
    ) -> ModelTurn:
        del prompt_version, prompt, tools
        case = _case_from(messages)
        narrative = str(case.get("narrative", ""))
        conditions = _conditions(narrative)
        quote = _quote(narrative)
        safety = bool(case.get("safety_relevant"))
        if agent == "intake":
            payload = {
                "summary": (
                    f"{case.get('component')} concern on "
                    f"{case.get('make')} {case.get('model')}"
                ),
                "group": case.get("group") or "unclear",
                "symptoms": [quote],
                "conditions": conditions,
                "fault_codes": [],
                "safety_relevant": safety,
                "missing_info": [],
                "clues": [{"kind": "symptom", "quote": quote}],
            }
        elif agent == "analysis":
            test_name = _test_name(conditions)
            payload = {
                "summary": f"Run the {test_name} for {case.get('component')}",
                "rationale": "The reported conditions match a targeted test rule.",
                "group": case.get("group") or "unclear",
                "symptoms": [quote],
                "conditions": conditions,
                "fault_codes": [],
                "safety_relevant": safety,
                "targeted": True,
                "test_name": test_name,
                "clues": [{"kind": "condition", "quote": quote}],
            }
        else:
            raise AssertionError(f"unexpected agent {agent!r}")
        return ModelTurn(
            text=json.dumps(payload, sort_keys=True),
            tokens=TOKENS,
            cost_usd=COST_USD,
            duration_ms=LATENCY_MS,
        )


class RecordingModel:
    """Wrap the scripted model and store a ChatResponse under the real key."""

    def __init__(self, model: AgentModel, store: RecordReplayStore) -> None:
        self._model = model
        self._store = store

    def complete(
        self,
        *,
        agent: str,
        prompt_version: str,
        prompt: str,
        messages: Sequence[Mapping[str, object]],
        tools: Sequence[Mapping[str, object]] = (),
    ) -> ModelTurn:
        turn = self._model.complete(
            agent=agent,
            prompt_version=prompt_version,
            prompt=prompt,
            messages=messages,
            tools=tools,
        )
        key = self._store.key(
            model=DEFAULT_MODEL,
            prompt_version=prompt_version,
            messages=messages,
            tools=tools,
        )
        response = ChatResponse(
            text=turn.text,
            tool_calls=(),
            finish_reason="stop",
            usage=Usage(
                input_tokens=TOKENS - 60,
                output_tokens=60,
                cost_usd=COST_USD,
            ),
            raw={},
            latency_ms=turn.duration_ms,
        )
        self._store.put(key, response)
        return turn


def main() -> int:
    store = RecordReplayStore(RECORDINGS, "record")
    model = RecordingModel(FixtureModel(), store)
    with (
        tempfile.TemporaryDirectory(prefix="fqa-recordings-") as temp,
        open_source(fixture_sql=FIXTURE_SQL) as source,
    ):
        summary = execute_run(
            source=source,
            recordings_dir=RECORDINGS,
            results_dir=Path(temp) / "runs",
            run_id="generation",
            set_name="replay_2025",
            mode=RunMode.REPLAY,
            model=model,
        )
    print(
        f"recordings: {summary.cases} cases, {len(list(RECORDINGS.rglob('*.json')))} files, "
        f"{summary.issues} issue(s), {summary.reports} report(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
