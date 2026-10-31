"""List prices from ``config/prices.toml`` and cost arithmetic.

PLAN §9 records the gateway's list cost when present; otherwise the token
counts are priced against this file. Prices are USD per million tokens and the
peak multiplier follows the windows verified in ``docs/NOTES-model.md``.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, time
from pathlib import Path

__all__ = ["DEFAULT_MODEL", "ModelPrice", "Prices", "default_prices"]

DEFAULT_MODEL = "deepseek-v4.1-flash"
DEFAULT_PRICES_PATH = Path("config/prices.toml")

_WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


@dataclass(frozen=True)
class ModelPrice:
    input_per_million: float
    output_per_million: float
    cached_input_per_million: float = 0.0
    peak_multiplier: float = 1.0

    def cost(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
        peak: bool,
    ) -> float:
        cached = max(0, min(cached_tokens, input_tokens))
        fresh = max(0, input_tokens - cached)
        multiplier = self.peak_multiplier if peak else 1.0
        total = (
            fresh * self.input_per_million
            + cached * self.cached_input_per_million
            + max(0, output_tokens) * self.output_per_million
        )
        return total / 1_000_000 * multiplier


@dataclass(frozen=True)
class Prices:
    models: Mapping[str, ModelPrice]
    peak_weekdays: frozenset[int] = frozenset({0, 1, 2, 3, 4})
    peak_windows: tuple[tuple[time, time], ...] = ()
    source: Path | None = None

    def price_for(self, model: str) -> ModelPrice:
        price = self.models.get(model) or self.models.get("default")
        if price is None:
            raise KeyError(f"no price for model {model!r} and no default entry")
        return price

    def is_peak(self, at: datetime) -> bool:
        moment = at.astimezone(UTC)
        if moment.weekday() not in self.peak_weekdays:
            return False
        current = moment.time().replace(tzinfo=None)
        return any(start <= current < end for start, end in self.peak_windows)

    def cost_usd(
        self,
        model: str,
        *,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        at: datetime | None = None,
    ) -> float:
        moment = at.astimezone(UTC) if at is not None else datetime.now(UTC)
        return self.price_for(model).cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            peak=self.is_peak(moment),
        )

    @classmethod
    def load(cls, path: Path = DEFAULT_PRICES_PATH) -> Prices:
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except FileNotFoundError:
            return default_prices()
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"invalid price file at {path}") from exc
        return _from_data(data, source=path)


def default_prices() -> Prices:
    """The committed values, available when the working directory is not the repo."""

    model = ModelPrice(
        input_per_million=0.15,
        output_per_million=0.60,
        cached_input_per_million=0.003,
        peak_multiplier=2.0,
    )
    return Prices(
        models={DEFAULT_MODEL: model, "default": model},
        peak_weekdays=frozenset({0, 1, 2, 3, 4}),
        peak_windows=((time(1, 0), time(4, 0)), (time(6, 0), time(10, 0))),
    )


def _from_data(data: Mapping[str, object], *, source: Path) -> Prices:
    peak_raw = data.get("peak", {})
    weekdays = frozenset({0, 1, 2, 3, 4})
    windows: tuple[tuple[time, time], ...] = ()
    if isinstance(peak_raw, Mapping):
        names = peak_raw.get("weekdays")
        if isinstance(names, list):
            weekdays = frozenset(
                _WEEKDAYS[name] for name in names if isinstance(name, str) and name in _WEEKDAYS
            )
        raw_windows = peak_raw.get("windows_utc")
        if isinstance(raw_windows, list):
            parsed: list[tuple[time, time]] = []
            for item in raw_windows:
                if isinstance(item, str):
                    window = _parse_window(item)
                    if window is not None:
                        parsed.append(window)
            windows = tuple(parsed)

    models_raw = data.get("models", {})
    models: dict[str, ModelPrice] = {}
    if isinstance(models_raw, Mapping):
        for name, raw in models_raw.items():
            if isinstance(name, str) and isinstance(raw, Mapping):
                models[name] = ModelPrice(
                    input_per_million=_number(raw.get("input_per_million")),
                    output_per_million=_number(raw.get("output_per_million")),
                    cached_input_per_million=_number(raw.get("cached_input_per_million")),
                    peak_multiplier=_number(raw.get("peak_multiplier"), default=1.0),
                )
    if not models:
        raise ValueError(f"no model prices in {source}")
    return Prices(models=models, peak_weekdays=weekdays, peak_windows=windows, source=source)


def _parse_window(value: str) -> tuple[time, time] | None:
    if "-" not in value:
        return None
    start_text, end_text = value.split("-", 1)
    try:
        return time.fromisoformat(start_text), time.fromisoformat(end_text)
    except ValueError:
        return None


def _number(value: object, *, default: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return default
    return float(value)
