"""Budget, pacing and request defaults from ``config/budget.toml``."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

__all__ = ["BudgetConfig", "PaceConfig", "RequestConfig", "RetryConfig"]

DEFAULT_BUDGET_PATH = Path("config/budget.toml")


@dataclass(frozen=True)
class PaceConfig:
    max_concurrent: int = 2
    per_minute: int = 30


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 8.0
    max_retry_after_seconds: float = 300.0


@dataclass(frozen=True)
class RequestConfig:
    temperature: float = 0.0
    max_tokens: int = 1024
    timeout_seconds: float = 60.0


@dataclass(frozen=True)
class BudgetConfig:
    max_steps: int = 12
    max_tokens: int = 40_000
    pace: PaceConfig = PaceConfig()
    retry: RetryConfig = RetryConfig()
    request: RequestConfig = RequestConfig()

    @classmethod
    def load(cls, path: Path = DEFAULT_BUDGET_PATH) -> BudgetConfig:
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except FileNotFoundError:
            return cls()
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"invalid budget file at {path}") from exc

        per_case = data.get("per_case", {})
        pace = data.get("pace", {})
        retry = data.get("retry", {})
        request = data.get("request", {})
        return cls(
            max_steps=_int(per_case, "max_steps", 12),
            max_tokens=_int(per_case, "max_tokens", 40_000),
            pace=PaceConfig(
                max_concurrent=_int(pace, "max_concurrent", 2),
                per_minute=_int(pace, "per_minute", 30),
            ),
            retry=RetryConfig(
                max_attempts=_int(retry, "max_attempts", 3),
                base_delay_seconds=_float(retry, "base_delay_seconds", 0.5),
                max_delay_seconds=_float(retry, "max_delay_seconds", 8.0),
                max_retry_after_seconds=_float(retry, "max_retry_after_seconds", 300.0),
            ),
            request=RequestConfig(
                temperature=_float(request, "temperature", 0.0),
                max_tokens=_int(request, "max_tokens", 1024),
                timeout_seconds=_float(request, "timeout_seconds", 60.0),
            ),
        )


def _value(section: object, key: str) -> object:
    if isinstance(section, dict):
        return section.get(key)
    return None


def _int(section: object, key: str, default: int) -> int:
    value = _value(section, key)
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value


def _float(section: object, key: str, default: float) -> float:
    value = _value(section, key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return default
    return float(value)
