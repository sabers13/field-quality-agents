"""The LangChain adapter: bind_tools, invoke, the desk protocol and replay."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from langchain_core.messages import HumanMessage
from llm_helpers import TOOL, completion, json_body, make_client, tool_call

from field_quality_agents.llm.errors import ReplayMissError
from field_quality_agents.llm.langchain_model import LangChainChatModel
from field_quality_agents.llm.recorder import RecordReplayStore


def test_bind_tools_and_invoke_return_an_ai_message() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json_body(request))
        return httpx.Response(200, json=completion(calls=[tool_call()]))

    model = LangChainChatModel(client=make_client(handler))
    bound = model.bind_tools([TOOL], tool_choice="required")
    assert isinstance(bound, LangChainChatModel)

    message = bound.invoke([HumanMessage(content="find similar cases")])

    assert message.content == ""
    assert len(message.tool_calls) == 1
    assert message.tool_calls[0]["name"] == "similar_cases"
    assert message.tool_calls[0]["args"] == {"text": "intermittent wiper", "k": 5}
    assert message.usage_metadata is not None
    assert message.usage_metadata["input_tokens"] == 100
    assert message.response_metadata["finish_reason"] == "tool_calls"

    assert bodies[0]["tools"] == [TOOL]
    assert bodies[0]["tool_choice"] == "required"
    assert bodies[0]["temperature"] == 0.0


def test_complete_implements_the_desk_protocol() -> None:
    payload = completion(
        text='{"summary": "ok"}',
        usage={"prompt_tokens": 100, "completion_tokens": 20},
    )
    model = LangChainChatModel(
        client=make_client(lambda request: httpx.Response(200, json=payload))
    )

    turn = model.complete(
        agent="intake",
        prompt_version="p1",
        prompt="system prompt",
        messages=[{"role": "user", "content": "normalise"}],
    )

    assert turn.text == '{"summary": "ok"}'
    assert turn.tokens == 120
    assert turn.cost_usd == pytest.approx(0.000027)


def test_replay_mode_reuses_the_recording_without_a_request(tmp_path: Path) -> None:
    calls: list[int] = []

    def record_handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, json=completion(calls=[tool_call()]))

    recorder = LangChainChatModel(
        client=make_client(record_handler),
        store=RecordReplayStore(tmp_path, "record"),
    )
    prompt = [HumanMessage(content="find similar cases")]
    recorded = recorder.bind_tools([TOOL]).invoke(prompt)
    assert len(calls) == 1

    def no_network(request: httpx.Request) -> httpx.Response:
        raise AssertionError("replay touched the network")

    replay = LangChainChatModel(
        client=make_client(no_network),
        store=RecordReplayStore(tmp_path, "replay"),
    )
    replayed = replay.bind_tools([TOOL]).invoke(prompt)

    assert replayed.content == recorded.content
    assert replayed.tool_calls == recorded.tool_calls


def test_replay_mode_raises_on_a_miss(tmp_path: Path) -> None:
    model = LangChainChatModel(
        client=make_client(lambda request: httpx.Response(500)),
        store=RecordReplayStore(tmp_path, "replay"),
    )
    with pytest.raises(ReplayMissError, match="no recording for key"):
        model.invoke([HumanMessage(content="never recorded")])
