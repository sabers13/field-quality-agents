"""OpenAI-compatible chat client with tools, retries, pacing and policy stop.

Verified endpoint and shapes: ``docs/NOTES-model.md``. The client owns every
network detail; the agents only see :class:`ChatResponse`. It retries transport
errors and 429 (honouring ``Retry-After``), never a bad answer. A 403 or an
abuse/policy warning raises :class:`PolicyStopError`, which writes
``reports/STOP.md`` (PLAN §10 rule 3).
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import cast

import httpx

from field_quality_agents.llm.budget import BudgetConfig
from field_quality_agents.llm.credentials import SecretKey, load_api_key
from field_quality_agents.llm.errors import (
    BadAnswerError,
    PolicyStopError,
    RateLimitError,
    TransportError,
)
from field_quality_agents.llm.models import ChatResponse, ToolCall, Usage
from field_quality_agents.llm.prices import DEFAULT_MODEL, Prices

__all__ = ["DEFAULT_BASE_URL", "USER_AGENT", "OpenAIChatClient", "Pacer"]

DEFAULT_BASE_URL = "https://opencode.ai/inference/go/openai/v1"
USER_AGENT = "field-quality-agents/0.1"
DEFAULT_STOP_PATH = Path("reports/STOP.md")
_SESSION_ID = f"fqa-{uuid.uuid4().hex}"
# Deliberately specific: a complaint narrative may quote the word "abuse", so
# the scanner needs an explicit policy/account phrase before it stops a run.
_POLICY_PHRASES = (
    "usage policy",
    "content policy",
    "abuse policy",
    "abuse detected",
    "policy violation",
    "account warning",
    "account has been suspended",
    "account is suspended",
    "request blocked",
    "violates the usage policy",
    "violates our policy",
    "not allowed to use this model",
)


class Pacer:
    """At most two requests in flight and thirty starts in any sixty seconds."""

    def __init__(
        self,
        *,
        max_concurrent: int = 2,
        per_minute: int = 30,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_concurrent < 1 or per_minute < 1:
            raise ValueError("pacing limits must be positive")
        self._slots = threading.BoundedSemaphore(max_concurrent)
        self._limit = per_minute
        self._clock = clock
        self._sleep = sleep
        self._starts: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        self._slots.acquire()
        try:
            self._wait_for_slot()
        except BaseException:
            self._slots.release()
            raise

    def release(self) -> None:
        self._slots.release()

    def __enter__(self) -> Pacer:
        self.acquire()
        return self

    def __exit__(self, *exc: object) -> None:
        self.release()

    def _wait_for_slot(self) -> None:
        while True:
            with self._lock:
                now = self._clock()
                while self._starts and now - self._starts[0] >= 60.0:
                    self._starts.popleft()
                if len(self._starts) < self._limit:
                    self._starts.append(now)
                    return
                delay = 60.0 - (now - self._starts[0])
            self._sleep(max(delay, 0.0))


class OpenAIChatClient:
    """One chat-completions client for the Go OpenAI-compatible endpoint."""

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        api_key: SecretKey | str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        prices: Prices | None = None,
        config: BudgetConfig | None = None,
        stop_path: Path = DEFAULT_STOP_PATH,
        pacer: Pacer | None = None,
        now: Callable[[], datetime] | None = None,
        timeout: float | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.prices = prices if prices is not None else Prices.load()
        self.config = config if config is not None else BudgetConfig.load()
        self.stop_path = Path(stop_path)
        self._clock = clock
        self._sleep = sleep
        self._now = now if now is not None else (lambda: datetime.now(UTC))
        self._api_key = _as_secret(api_key)
        self._pacer = pacer if pacer is not None else Pacer(
            max_concurrent=self.config.pace.max_concurrent,
            per_minute=self.config.pace.per_minute,
            clock=clock,
            sleep=sleep,
        )
        seconds = timeout if timeout is not None else self.config.request.timeout_seconds
        self._http = httpx.Client(
            base_url=self.base_url,
            transport=transport,
            timeout=httpx.Timeout(seconds),
        )

    def __repr__(self) -> str:
        return f"OpenAIChatClient(model={self.model!r}, base_url={self.base_url!r})"

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> OpenAIChatClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def chat(
        self,
        *,
        messages: Sequence[Mapping[str, object]],
        tools: Sequence[Mapping[str, object]] = (),
        tool_choice: str = "auto",
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> ChatResponse:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [dict(message) for message in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = [dict(tool) for tool in tools]
            payload["tool_choice"] = tool_choice

        attempts = self.config.retry.max_attempts
        for attempt in range(1, attempts + 1):
            try:
                with self._pacer:
                    started = self._clock()
                    response = self._http.post(
                        "chat/completions",
                        json=payload,
                        headers=self._headers(),
                    )
            except httpx.TransportError as exc:
                if attempt >= attempts:
                    raise TransportError(
                        f"transport error after {attempt} attempt(s): {type(exc).__name__}"
                    ) from exc
                self._sleep(self._backoff(attempt))
                continue

            latency_ms = int((self._clock() - started) * 1000)
            status = response.status_code
            if status == 429:
                retry_after = _retry_after(response.headers.get("retry-after"), self._now())
                if attempt >= attempts:
                    raise RateLimitError(
                        f"HTTP 429 after {attempt} attempt(s)",
                        retry_after=retry_after,
                    )
                delay = retry_after if retry_after is not None else self._backoff(attempt)
                self._sleep(min(delay, self.config.retry.max_retry_after_seconds))
                continue
            if status == 403:
                raise PolicyStopError(
                    f"HTTP 403 from the model endpoint: {_short_body(response)}",
                    stop_path=self.stop_path,
                )
            if status < 200 or status >= 300:
                body = _short_body(response)
                if _looks_like_policy(body):
                    raise PolicyStopError(
                        f"HTTP {status} from the model endpoint carries a policy warning: {body}",
                        stop_path=self.stop_path,
                    )
                raise TransportError(
                    f"HTTP {status} from the model endpoint: {body}",
                    status_code=status,
                )
            return self._parse(response.text, tools=tools, latency_ms=latency_ms)

        raise TransportError("the retry loop ended without a response")

    def _headers(self) -> dict[str, str]:
        key = self._api_key
        if key is None:
            key = load_api_key()
            self._api_key = key
        return {
            "Authorization": f"Bearer {key.reveal()}",
            "User-Agent": USER_AGENT,
            "x-opencode-session": _SESSION_ID,
            "Accept": "application/json",
        }

    def _backoff(self, attempt: int) -> float:
        retry = self.config.retry
        return float(
            min(retry.base_delay_seconds * (2 ** (attempt - 1)), retry.max_delay_seconds)
        )

    def _parse(
        self,
        body: str,
        *,
        tools: Sequence[Mapping[str, object]],
        latency_ms: int,
    ) -> ChatResponse:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise BadAnswerError("the model response body is not JSON") from exc
        if not isinstance(payload, dict):
            raise BadAnswerError("the model response is not a JSON object")
        data = cast(dict[str, object], payload)

        error = data.get("error")
        if error is not None:
            error_text = _error_message(error)
            if _looks_like_policy(error_text):
                raise PolicyStopError(
                    f"the model endpoint returned a policy error: {_truncate(error_text)}",
                    stop_path=self.stop_path,
                )
            raise BadAnswerError(
                f"the model endpoint returned an error: {_truncate(error_text)}"
            )

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise BadAnswerError("the model response has no choices")
        first = choices[0]
        if not isinstance(first, Mapping):
            raise BadAnswerError("the first choice is not an object")
        finish_reason = first.get("finish_reason")
        if not isinstance(finish_reason, str) or not finish_reason:
            raise BadAnswerError("the model response has no finish_reason")
        message = first.get("message")
        if not isinstance(message, Mapping):
            raise BadAnswerError("the first choice has no message")

        content = message.get("content")
        if content is None:
            text = ""
        elif isinstance(content, str):
            text = content
        else:
            raise BadAnswerError("the assistant content is not text")

        calls = self._tool_calls(message.get("tool_calls"), tools)
        if finish_reason == "tool_calls" and not calls:
            raise BadAnswerError("finish_reason is tool_calls but no tool call is present")
        if not text and not calls:
            raise BadAnswerError("the model answer is empty")
        if _looks_like_policy(text):
            raise PolicyStopError(
                f"the model answer carries a policy warning: {_truncate(text)}",
                stop_path=self.stop_path,
            )

        usage = self._usage(data.get("usage"))
        return ChatResponse(
            text=text,
            tool_calls=calls,
            finish_reason=finish_reason,
            usage=usage,
            raw=data,
            latency_ms=latency_ms,
        )

    def _tool_calls(
        self,
        raw: object,
        tools: Sequence[Mapping[str, object]],
    ) -> tuple[ToolCall, ...]:
        if raw is None:
            return ()
        if not isinstance(raw, list):
            raise BadAnswerError("tool_calls is not a list")
        known = _tool_names(tools)
        calls: list[ToolCall] = []
        for item in raw:
            if not isinstance(item, Mapping):
                raise BadAnswerError("a tool call is not an object")
            call_id = item.get("id")
            if not isinstance(call_id, str) or not call_id:
                raise BadAnswerError("a tool call has no id")
            function = item.get("function")
            if not isinstance(function, Mapping):
                raise BadAnswerError("a tool call has no function")
            name = function.get("name")
            if not isinstance(name, str) or not name:
                raise BadAnswerError("a tool call has no function name")
            if known and name not in known:
                raise BadAnswerError(f"the model called an unknown tool: {name!r}")
            arguments_raw = function.get("arguments")
            if not isinstance(arguments_raw, str):
                raise BadAnswerError("tool call arguments are not a JSON string")
            try:
                arguments = json.loads(arguments_raw)
            except json.JSONDecodeError as exc:
                raise BadAnswerError("tool call arguments are not valid JSON") from exc
            if not isinstance(arguments, dict):
                raise BadAnswerError("tool call arguments are not a JSON object")
            calls.append(
                ToolCall(
                    id=call_id,
                    name=name,
                    arguments={str(key): value for key, value in arguments.items()},
                )
            )
        return tuple(calls)

    def _usage(self, raw: object) -> Usage:
        usage = raw if isinstance(raw, Mapping) else {}
        input_tokens = _int(usage.get("prompt_tokens"))
        output_tokens = _int(usage.get("completion_tokens"))
        completion_details = usage.get("completion_tokens_details")
        prompt_details = usage.get("prompt_tokens_details")
        reasoning_tokens = _int(
            completion_details.get("reasoning_tokens")
            if isinstance(completion_details, Mapping)
            else None
        )
        cached_tokens = _int(
            prompt_details.get("cached_tokens") if isinstance(prompt_details, Mapping) else None
        )

        opencode = usage.get("opencode")
        opencode_map = opencode if isinstance(opencode, Mapping) else {}
        list_cost = _float_or_none(opencode_map.get("list_cost"))
        allowance = _float_or_none(opencode_map.get("allowance"))
        gateway_cost = _float_or_none(usage.get("cost"))

        if list_cost is not None:
            cost = list_cost
        elif gateway_cost is not None and gateway_cost > 0:
            cost = gateway_cost
        else:
            cost = self.prices.cost_usd(
                self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=cached_tokens,
                at=self._now(),
            )

        return Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            cached_tokens=cached_tokens,
            cost_usd=cost,
            list_cost_usd=list_cost,
            allowance_usd=allowance,
        )


def _as_secret(value: SecretKey | str | None) -> SecretKey | None:
    if value is None or isinstance(value, SecretKey):
        return value
    return SecretKey(value)


def _tool_names(tools: Sequence[Mapping[str, object]]) -> set[str]:
    names: set[str] = set()
    for tool in tools:
        function = tool.get("function")
        if isinstance(function, Mapping):
            name = function.get("name")
            if isinstance(name, str) and name:
                names.add(name)
    return names


def _int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


def _float_or_none(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _error_message(error: object) -> str:
    if isinstance(error, str):
        return error
    if isinstance(error, Mapping):
        message = error.get("message")
        return message if isinstance(message, str) else _canonical(error)
    return _canonical(error)


def _canonical(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return str(value)


def _looks_like_policy(text: str) -> bool:
    lowered = text.lower()
    if not lowered:
        return False
    return any(phrase in lowered for phrase in _POLICY_PHRASES)


def _truncate(text: str) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= 240 else cleaned[:237] + "..."


def _short_body(response: httpx.Response) -> str:
    try:
        return _truncate(response.text)
    except Exception:
        return "<unreadable body>"


def _retry_after(value: str | None, now: datetime) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        moment = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return max(0.0, (moment - now).total_seconds())
