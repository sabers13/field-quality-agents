"""Record and replay model turns.

PLAN §3: every live response is stored under ``recordings/``, keyed by
``sha256(model + prompt version + canonical messages + tools)``; replay never
touches the network and raises :class:`ReplayMissError` instead of guessing.

Layout: ``<root>/<first two hex chars>/<key>.json`` so a full live run does not
put thousands of files in one directory.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, Protocol

from field_quality_agents.llm.errors import ReplayMissError
from field_quality_agents.llm.models import ChatResponse, response_from_dict, response_to_dict
from field_quality_agents.llm.prices import DEFAULT_MODEL

__all__ = ["ChatTransport", "RecordReplayChatClient", "RecordReplayStore"]

Mode = Literal["record", "replay"]


class ChatTransport(Protocol):
    def chat(
        self,
        *,
        messages: Sequence[Mapping[str, object]],
        tools: Sequence[Mapping[str, object]] = (),
        tool_choice: str = "auto",
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> ChatResponse: ...


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


class RecordReplayStore:
    """A directory of recorded turns, read or written by key."""

    def __init__(self, root: Path, mode: Mode) -> None:
        if mode not in ("record", "replay"):
            raise ValueError("mode must be 'record' or 'replay'")
        self.root = Path(root)
        self.mode: Mode = mode

    def key(
        self,
        *,
        model: str,
        prompt_version: str,
        messages: Sequence[Mapping[str, object]],
        tools: Sequence[Mapping[str, object]],
    ) -> str:
        import hashlib

        body = canonical_json(
            {
                "model": model,
                "prompt_version": prompt_version,
                "messages": list(messages),
                "tools": list(tools),
            }
        )
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def path_for(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def _candidate_paths(self, key: str) -> tuple[Path, ...]:
        # Sharded layout is the writer's choice; a flat ``<key>.json`` is
        # accepted on read so recordings copied from another checkout replay.
        return (self.path_for(key), self.root / f"{key}.json")

    def has(self, key: str) -> bool:
        return any(path.is_file() for path in self._candidate_paths(key))

    def get(self, key: str) -> ChatResponse:
        path = next(
            (candidate for candidate in self._candidate_paths(key) if candidate.is_file()),
            None,
        )
        if path is None:
            raise ReplayMissError(key)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ReplayMissError(key) from exc
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"recording {key} is not valid JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("response"), dict):
            raise ValueError(f"recording {key} has no response object")
        return response_from_dict(payload["response"])

    def put(self, key: str, response: ChatResponse) -> None:
        if self.mode != "record":
            raise RuntimeError("the replay store is read-only")
        path = self.path_for(key)
        if path.exists():
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "key": key,
            "response": response_to_dict(response),
        }
        text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        handle, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(text)
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)


class RecordReplayChatClient:
    """Wrap the HTTP client: replay from the store, or record a live answer."""

    def __init__(
        self,
        *,
        client: ChatTransport,
        store: RecordReplayStore,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self.client = client
        self.store = store
        self.model = model

    def chat(
        self,
        *,
        messages: Sequence[Mapping[str, object]],
        tools: Sequence[Mapping[str, object]] = (),
        tool_choice: str = "auto",
        temperature: float = 0.0,
        max_tokens: int = 1024,
        prompt_version: str = "p1",
    ) -> ChatResponse:
        key = self.store.key(
            model=self.model,
            prompt_version=prompt_version,
            messages=messages,
            tools=tools,
        )
        try:
            return self.store.get(key)
        except ReplayMissError:
            if self.store.mode == "replay":
                raise
        response = self._live_chat(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.store.put(key, response)
        return response

    def _live_chat(
        self,
        *,
        messages: Sequence[Mapping[str, object]],
        tools: Sequence[Mapping[str, object]],
        tool_choice: str,
        temperature: float,
        max_tokens: int,
    ) -> ChatResponse:
        return self.client.chat(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
        )