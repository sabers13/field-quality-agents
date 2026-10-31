"""Q4 model lane: OpenAI-compatible chat, cost, record/replay and LangChain."""

from __future__ import annotations

from field_quality_agents.llm.budget import BudgetConfig, PaceConfig, RequestConfig, RetryConfig
from field_quality_agents.llm.client import DEFAULT_BASE_URL, USER_AGENT, OpenAIChatClient, Pacer
from field_quality_agents.llm.credentials import SecretKey, load_api_key
from field_quality_agents.llm.errors import (
    BadAnswerError,
    CredentialError,
    ModelError,
    PolicyStopError,
    RateLimitError,
    ReplayMissError,
    TransportError,
)
from field_quality_agents.llm.langchain_model import LangChainChatModel
from field_quality_agents.llm.models import ChatResponse, ToolCall, Usage
from field_quality_agents.llm.prices import DEFAULT_MODEL, ModelPrice, Prices
from field_quality_agents.llm.recorder import RecordReplayChatClient, RecordReplayStore

__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
    "USER_AGENT",
    "BadAnswerError",
    "BudgetConfig",
    "ChatResponse",
    "CredentialError",
    "LangChainChatModel",
    "ModelError",
    "ModelPrice",
    "OpenAIChatClient",
    "PaceConfig",
    "Pacer",
    "PolicyStopError",
    "Prices",
    "RateLimitError",
    "RecordReplayChatClient",
    "RecordReplayStore",
    "ReplayMissError",
    "RequestConfig",
    "RetryConfig",
    "SecretKey",
    "ToolCall",
    "TransportError",
    "Usage",
    "load_api_key",
]
