"""Client behaviour: tools, retries, policy stop, bad answers, pacing and cost."""

from __future__ import annotations

import math
import threading
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from llm_helpers import (
    OFF_PEAK,
    PEAK,
    TOOL,
    completion,
    json_body,
    make_client,
    tool_call,
)

from field_quality_agents.llm.client import USER_AGENT, Pacer, _retry_after
from field_quality_agents.llm.errors import (
    BadAnswerError,
    PolicyStopError,
    RateLimitError,
    TransportError,
)
from field_quality_agents.llm.prices import default_prices


def test_success_parses_tool_call_and_request_shape() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=completion(calls=[tool_call()]))

    client = make_client(handler)
    response = client.chat(
        messages=[{"role": "user", "content": "find similar cases"}],
        tools=[TOOL],
    )

    assert response.text == ""
    assert response.finish_reason == "tool_calls"
    assert len(response.tool_calls) == 1
    call = response.tool_calls[0]
    assert call.id == "call_1"
    assert call.name == "similar_cases"
    assert call.arguments == {"text": "intermittent wiper", "k": 5}
    assert response.usage.input_tokens == 100
    assert response.usage.output_tokens == 20
    assert response.usage.total_tokens == 120
    assert response.latency_ms >= 0
    assert response.raw["model"] == "deepseek-v4.1-flash"

    assert len(seen) == 1
    request = seen[0]
    assert str(request.url) == (
        "https://opencode.ai/inference/go/openai/v1/chat/completions"
    )
    assert request.headers["user-agent"] == USER_AGENT
    assert request.headers["authorization"].startswith("Bearer ")
    assert request.headers["x-opencode-session"]
    body = json_body(request)
    assert body["model"] == "deepseek-v4.1-flash"
    assert body["temperature"] == 0.0
    assert body["max_tokens"] == 1024
    assert body["tool_choice"] == "auto"
    assert body["tools"] == [TOOL]


def test_cost_comes_from_usage_tokens_when_gateway_has_no_cost() -> None:
    payload = completion(
        text="ok",
        usage={"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000},
    )
    client = make_client(lambda request: httpx.Response(200, json=payload))
    response = client.chat(messages=[{"role": "user", "content": "hi"}])

    # Off-peak: USD 0.15 input + USD 0.60 output per million.
    assert response.usage.cost_usd == pytest.approx(0.75)
    assert response.usage.list_cost_usd is None


def test_gateway_list_cost_and_allowance_are_recorded() -> None:
    payload = completion(
        text="ok",
        usage={
            "prompt_tokens": 332,
            "completion_tokens": 74,
            "cost": 0,
            "opencode": {
                "billing_source": "go",
                "list_cost": 0.0000942,
                "allowance": 0.00005652,
            },
        },
    )
    client = make_client(lambda request: httpx.Response(200, json=payload))
    usage = client.chat(messages=[{"role": "user", "content": "hi"}]).usage

    assert usage.cost_usd == pytest.approx(0.0000942)
    assert usage.list_cost_usd == pytest.approx(0.0000942)
    assert usage.allowance_usd == pytest.approx(0.00005652)


def test_peak_multiplier_applies_when_priced_locally() -> None:
    payload = completion(
        text="ok", usage={"prompt_tokens": 1_000_000, "completion_tokens": 0}
    )
    client = make_client(
        lambda request: httpx.Response(200, json=payload),
        prices=default_prices(),
        now=lambda: PEAK,
    )
    usage = client.chat(messages=[{"role": "user", "content": "hi"}]).usage
    assert usage.cost_usd == pytest.approx(0.30)


def test_429_honours_retry_after_and_retries() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "3"}, json={"error": "slow"})
        return httpx.Response(200, json=completion(text="after the wait"))

    client = make_client(handler)
    response = client.chat(messages=[{"role": "user", "content": "hi"}])

    assert response.text == "after the wait"
    assert len(calls) == 2
    assert client.recorded_sleeps == [3.0]  # type: ignore[attr-defined]


def test_429_without_retry_after_uses_bounded_backoff() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(429, json={"error": "slow"})

    client = make_client(handler, attempts=3)
    with pytest.raises(RateLimitError) as raised:
        client.chat(messages=[{"role": "user", "content": "hi"}])

    assert raised.value.retry_after is None
    assert raised.value.status_code == 429
    assert len(calls) == 3
    assert client.recorded_sleeps == [0.5, 1.0]  # type: ignore[attr-defined]


def test_transport_error_retries_then_succeeds() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ConnectError("temporary", request=request)
        return httpx.Response(200, json=completion(text="recovered"))

    client = make_client(handler)
    response = client.chat(messages=[{"role": "user", "content": "hi"}])

    assert response.text == "recovered"
    assert len(calls) == 2
    assert client.recorded_sleeps == [0.5]  # type: ignore[attr-defined]


def test_transport_error_exhausts_attempts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    client = make_client(handler, attempts=2)
    with pytest.raises(TransportError, match="transport error after 2 attempt"):
        client.chat(messages=[{"role": "user", "content": "hi"}])


def test_403_writes_stop_report_and_never_retries(tmp_path: Path) -> None:
    calls: list[int] = []
    stop = tmp_path / "STOP.md"

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(403, json={"error": {"message": "forbidden"}})

    client = make_client(handler, stop_path=stop)
    with pytest.raises(PolicyStopError, match="HTTP 403"):
        client.chat(messages=[{"role": "user", "content": "hi"}])

    assert len(calls) == 1
    text = stop.read_text(encoding="utf-8")
    assert "PLAN §10 rule 3" in text
    assert "forbidden" in text


def test_bad_answer_is_never_retried() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, json=completion(calls=[tool_call(arguments="{not json")]))

    client = make_client(handler)
    with pytest.raises(BadAnswerError, match="arguments are not valid JSON"):
        client.chat(messages=[{"role": "user", "content": "hi"}], tools=[TOOL])
    assert len(calls) == 1


def test_empty_answer_is_a_bad_answer() -> None:
    client = make_client(
        lambda request: httpx.Response(200, json=completion(text=None, finish_reason="stop"))
    )
    with pytest.raises(BadAnswerError, match="answer is empty"):
        client.chat(messages=[{"role": "user", "content": "hi"}])


def test_missing_choices_is_a_bad_answer() -> None:
    client = make_client(lambda request: httpx.Response(200, json={"choices": []}))
    with pytest.raises(BadAnswerError, match="no choices"):
        client.chat(messages=[{"role": "user", "content": "hi"}])


def test_bad_answer_on_unknown_tool() -> None:
    payload = completion(calls=[tool_call(name="not_a_tool")])
    client = make_client(lambda request: httpx.Response(200, json=payload))
    with pytest.raises(BadAnswerError, match="unknown tool"):
        client.chat(messages=[{"role": "user", "content": "hi"}], tools=[TOOL])


def test_non_json_body_is_a_bad_answer() -> None:
    client = make_client(lambda request: httpx.Response(200, text="<html>nope</html>"))
    with pytest.raises(BadAnswerError, match="not JSON"):
        client.chat(messages=[{"role": "user", "content": "hi"}])


def test_policy_text_in_a_200_answer_stops_the_run(tmp_path: Path) -> None:
    stop = tmp_path / "STOP.md"
    payload = completion(text="Request blocked by abuse policy.")
    client = make_client(
        lambda request: httpx.Response(200, json=payload),
        stop_path=stop,
    )
    with pytest.raises(PolicyStopError, match="policy warning"):
        client.chat(messages=[{"role": "user", "content": "hi"}])
    assert "abuse policy" in stop.read_text(encoding="utf-8")


def test_policy_text_in_an_error_object_stops_the_run(tmp_path: Path) -> None:
    stop = tmp_path / "STOP.md"
    payload = {"error": {"message": "usage policy violation on this account"}}
    client = make_client(
        lambda request: httpx.Response(400, json=payload),
        stop_path=stop,
    )
    with pytest.raises(PolicyStopError, match="policy"):
        client.chat(messages=[{"role": "user", "content": "hi"}])
    assert stop.is_file()


def test_other_http_errors_are_transport_errors() -> None:
    client = make_client(lambda request: httpx.Response(500, text="upstream down"))
    with pytest.raises(TransportError) as raised:
        client.chat(messages=[{"role": "user", "content": "hi"}])
    assert raised.value.status_code == 500


def test_retry_after_accepts_http_dates() -> None:
    now = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
    assert _retry_after("Sat, 31 Oct 2026 12:00:30 GMT", now) == pytest.approx(30.0)
    assert _retry_after("7", now) == 7.0
    assert _retry_after("nonsense", now) is None


def test_pacer_allows_thirty_per_minute_without_sleeping() -> None:
    now = [0.0]
    sleeps: list[float] = []

    def clock() -> float:
        return now[0]

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    pacer = Pacer(per_minute=30, clock=clock, sleep=sleep)
    for _ in range(30):
        with pacer:
            now[0] += 0.1
    assert sleeps == []
    with pacer:
        pass
    assert sleeps == [pytest.approx(57.0)]


def test_pacer_enforces_two_concurrent_requests() -> None:
    pacer = Pacer(max_concurrent=2)
    pacer.acquire()
    pacer.acquire()

    acquired = threading.Event()

    def third() -> None:
        pacer.acquire()
        acquired.set()
        pacer.release()

    thread = threading.Thread(target=third, daemon=True)
    thread.start()
    assert not acquired.wait(0.1)

    pacer.release()
    assert acquired.wait(1.0)
    thread.join(timeout=1.0)
    pacer.release()


def test_latency_uses_injected_clock() -> None:
    now = [0.0]

    def handler(request: httpx.Request) -> httpx.Response:
        now[0] += 0.25
        return httpx.Response(200, json=completion(text="ok"))

    client = make_client(handler, clock=lambda: now[0])
    response = client.chat(messages=[{"role": "user", "content": "hi"}])
    assert response.latency_ms == 250


def test_unknown_model_price_falls_back_to_default() -> None:
    prices = default_prices()
    assert math.isclose(
        prices.cost_usd("some-other-model", input_tokens=1_000_000, output_tokens=0, at=OFF_PEAK),
        0.15,
    )


def test_client_repr_does_not_contain_the_key() -> None:
    client = make_client(lambda request: httpx.Response(200, json=completion(text="ok")))
    assert "test" not in repr(client)
