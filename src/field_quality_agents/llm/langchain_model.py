"""LangChain chat-model adapter for the Q4 client.

LangGraph needs a ``BaseChatModel`` that can ``bind_tools``; the desk's own
``AgentModel`` protocol needs ``complete``. This class implements both on top of
the same record/replay path, so a graph behaves identically in record and
replay modes and never touches the network in replay.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, convert_to_openai_messages
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import Field

from field_quality_agents.agents.model import ModelTurn
from field_quality_agents.llm.client import OpenAIChatClient
from field_quality_agents.llm.models import ChatResponse
from field_quality_agents.llm.prices import DEFAULT_MODEL
from field_quality_agents.llm.recorder import RecordReplayChatClient, RecordReplayStore

__all__ = ["LangChainChatModel"]


class LangChainChatModel(BaseChatModel):
    """A chat model with tools that records or replays every turn."""

    client: OpenAIChatClient = Field(default_factory=OpenAIChatClient)
    store: RecordReplayStore | None = None
    model: str = DEFAULT_MODEL
    prompt_version: str = "p1"
    temperature: float = 0.0
    max_tokens: int = 8192
    tool_choice: str = "auto"
    bound_tools: tuple[dict[str, object], ...] = ()

    @property
    def _llm_type(self) -> str:
        return "field-quality-agents-openai-compatible"

    @property
    def _identifying_params(self) -> dict[str, object]:
        return {
            "model": self.model,
            "base_url": self.client.base_url,
            "prompt_version": self.prompt_version,
            "mode": self.store.mode if self.store is not None else "live",
        }

    def bind_tools(
        self,
        tools: Sequence[object],
        *,
        tool_choice: str | None = None,
        **kwargs: object,
    ) -> LangChainChatModel:
        """Return a copy with OpenAI tool specs attached (LangGraph calls this)."""

        del kwargs
        specs: list[dict[str, object]] = []
        for tool in tools:
            converted = convert_to_openai_tool(cast(Any, tool))
            specs.append(cast(dict[str, object], converted))
        choice = tool_choice or self.tool_choice
        return self.model_copy(
            update={"bound_tools": tuple(specs), "tool_choice": choice}
        )

    def complete(
        self,
        *,
        agent: str,
        prompt_version: str,
        prompt: str,
        messages: Sequence[Mapping[str, object]],
        tools: Sequence[Mapping[str, object]] = (),
    ) -> ModelTurn:
        """The desk's small protocol: one turn with text, tokens and cost."""

        del agent, prompt
        response = self._answer(
            messages=[dict(message) for message in messages],
            tools=[dict(tool) for tool in tools],
            prompt_version=prompt_version,
            tool_choice=self.tool_choice,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return ModelTurn(
            text=response.text,
            tokens=response.usage.total_tokens,
            cost_usd=response.usage.cost_usd or 0.0,
            duration_ms=response.latency_ms,
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        del stop, run_manager
        prompt_version = str(kwargs.get("prompt_version", self.prompt_version))
        tools = cast(
            Sequence[Mapping[str, object]],
            kwargs.get("tools", self.bound_tools),
        )
        tool_choice = str(kwargs.get("tool_choice", self.tool_choice))
        temperature = float(kwargs.get("temperature", self.temperature))
        max_tokens = int(kwargs.get("max_tokens", self.max_tokens))

        openai_messages = cast(
            list[dict[str, object]], convert_to_openai_messages(messages)
        )
        response = self._answer(
            messages=openai_messages,
            tools=[dict(tool) for tool in tools],
            prompt_version=prompt_version,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return ChatResult(generations=[ChatGeneration(message=_ai_message(response, self.model))])

    def _answer(
        self,
        *,
        messages: Sequence[Mapping[str, object]],
        tools: Sequence[Mapping[str, object]],
        prompt_version: str,
        tool_choice: str,
        temperature: float,
        max_tokens: int,
    ) -> ChatResponse:
        if self.store is None:
            return self.client.chat(
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        gateway = RecordReplayChatClient(client=self.client, store=self.store, model=self.model)
        return gateway.chat(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
            prompt_version=prompt_version,
        )


def _ai_message(response: ChatResponse, model: str) -> AIMessage:
    return AIMessage(
        content=response.text,
        tool_calls=[
            {"name": call.name, "args": call.arguments, "id": call.id, "type": "tool_call"}
            for call in response.tool_calls
        ],
        usage_metadata={
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.total_tokens,
        },
        response_metadata={
            "model": model,
            "finish_reason": response.finish_reason,
            "cost_usd": response.usage.cost_usd,
            "latency_ms": response.latency_ms,
            "provider": "opencode-go",
        },
    )
