"""Record/replay: stable keys, a hit makes no request, a miss raises."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from llm_helpers import TOOL, completion, make_client, tool_call

from field_quality_agents.llm.errors import ReplayMissError
from field_quality_agents.llm.models import response_from_dict, response_to_dict
from field_quality_agents.llm.recorder import (
    RecordReplayChatClient,
    RecordReplayStore,
    canonical_json,
)


def _recording_client(root: Path, calls: list[int]) -> RecordReplayChatClient:
    client = make_client(
        lambda request: (
            calls.append(1)
            or httpx.Response(200, json=completion(calls=[tool_call()]))
        )
    )
    return RecordReplayChatClient(
        client=client, store=RecordReplayStore(root, "record")
    )


def test_record_then_replay_without_a_request(tmp_path: Path) -> None:
    calls: list[int] = []
    recorder = _recording_client(tmp_path, calls)
    messages = [{"role": "user", "content": "find similar cases"}]

    first = recorder.chat(messages=messages, tools=[TOOL], prompt_version="p1")
    assert len(calls) == 1
    key = recorder.store.key(
        model=recorder.model,
        prompt_version="p1",
        messages=messages,
        tools=[TOOL],
    )
    assert recorder.store.path_for(key).is_file()

    def no_network(request: httpx.Request) -> httpx.Response:
        raise AssertionError("replay touched the network")

    replay = RecordReplayChatClient(
        client=make_client(no_network),
        store=RecordReplayStore(tmp_path, "replay"),
    )
    second = replay.chat(messages=messages, tools=[TOOL], prompt_version="p1")

    assert second == first
    assert second.tool_calls[0].arguments == {"text": "intermittent wiper", "k": 5}


def test_replay_miss_raises_and_makes_no_request(tmp_path: Path) -> None:
    def no_network(request: httpx.Request) -> httpx.Response:
        raise AssertionError("replay touched the network")

    replay = RecordReplayChatClient(
        client=make_client(no_network),
        store=RecordReplayStore(tmp_path, "replay"),
    )
    with pytest.raises(ReplayMissError):
        replay.chat(messages=[{"role": "user", "content": "never recorded"}])
    assert list(tmp_path.rglob("*.json")) == []


def test_key_ignores_dict_insertion_order_and_ignores_prompt_text_order(
    tmp_path: Path,
) -> None:
    store = RecordReplayStore(tmp_path, "replay")
    key_a = store.key(
        model="m",
        prompt_version="p1",
        messages=[{"role": "user", "content": "x"}],
        tools=[{"type": "function", "function": {"name": "f"}}],
    )
    key_b = store.key(
        model="m",
        prompt_version="p1",
        messages=[{"content": "x", "role": "user"}],
        tools=[{"function": {"name": "f"}, "type": "function"}],
    )
    key_c = store.key(
        model="m",
        prompt_version="p2",
        messages=[{"role": "user", "content": "x"}],
        tools=[{"type": "function", "function": {"name": "f"}}],
    )
    assert key_a == key_b
    assert key_a != key_c
    assert len(key_a) == 64


def test_replay_store_is_read_only(tmp_path: Path) -> None:
    store = RecordReplayStore(tmp_path, "replay")
    recorder = _recording_client(tmp_path / "source", [])
    response = recorder.chat(messages=[{"role": "user", "content": "hi"}])
    key = store.key(
        model="m", prompt_version="p1", messages=[], tools=[]
    )
    with pytest.raises(RuntimeError, match="read-only"):
        store.put(key, response)


def test_recording_envelope_round_trips(tmp_path: Path) -> None:
    recorder = _recording_client(tmp_path, [])
    response = recorder.chat(messages=[{"role": "user", "content": "hi"}])
    assert response == response_from_dict(response_to_dict(response))


def test_canonical_json_is_stable() -> None:
    assert canonical_json({"b": 1, "a": [2, 3]}) == '{"a":[2,3],"b":1}'


def test_flat_recording_layout_is_accepted_on_read(tmp_path: Path) -> None:
    recorder = _recording_client(tmp_path / "source", [])
    response = recorder.chat(messages=[{"role": "user", "content": "hi"}])

    flat_root = tmp_path / "flat"
    flat_root.mkdir()
    store = RecordReplayStore(flat_root, "replay")
    key = store.key(
        model="m", prompt_version="p1", messages=[], tools=[]
    )
    (flat_root / f"{key}.json").write_text(
        '{"key": "' + key + '", "response": ' + json.dumps(response_to_dict(response)) + "}",
        encoding="utf-8",
    )
    assert store.get(key) == response
