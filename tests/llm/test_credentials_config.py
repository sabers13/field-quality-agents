"""Credentials and configuration: precedence, redaction, prices and budgets."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from field_quality_agents.llm.budget import BudgetConfig
from field_quality_agents.llm.credentials import SecretKey, load_api_key
from field_quality_agents.llm.errors import CredentialError
from field_quality_agents.llm.prices import DEFAULT_MODEL, Prices, default_prices


def test_key_loads_from_env_file_and_redacts_itself(tmp_path: Path) -> None:
    env = tmp_path / "upstream.env"
    env.write_text("# comment\nOPENCODE_API_KEY='fake-value'\n", encoding="utf-8")
    key = load_api_key(env, dotenv=tmp_path / "missing.env")

    assert key.reveal() == "fake-value"
    assert "fake-value" not in repr(key)
    assert "fake-value" not in str(key)
    assert str(key) == "<redacted>"


def test_fqa_env_file_wins_over_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = tmp_path / "from-variable.env"
    env.write_text("OPENAI_API_KEY=first\n", encoding="utf-8")
    dotenv = tmp_path / ".env"
    dotenv.write_text("OPENAI_API_KEY=second\n", encoding="utf-8")
    monkeypatch.setenv("FQA_ENV_FILE", str(env))

    assert load_api_key(dotenv=dotenv).reveal() == "first"


def test_dotenv_is_the_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FQA_ENV_FILE", str(tmp_path / "absent.env"))
    dotenv = tmp_path / ".env"
    dotenv.write_text("export FQA_API_KEY=from-dotenv\n", encoding="utf-8")

    assert load_api_key(dotenv=dotenv).reveal() == "from-dotenv"


def test_single_unknown_assignment_is_accepted(tmp_path: Path) -> None:
    env = tmp_path / "probe.env"
    env.write_text('SOME_PROVIDER_TOKEN="single"\n', encoding="utf-8")
    assert load_api_key(env, dotenv=tmp_path / "missing").reveal() == "single"


def test_missing_key_raises_without_leaking_contents(tmp_path: Path) -> None:
    env = tmp_path / "empty.env"
    env.write_text("# nothing here\n", encoding="utf-8")
    with pytest.raises(CredentialError) as raised:
        load_api_key(env, dotenv=tmp_path / "missing")
    assert "nothing here" not in str(raised.value)
    assert "empty.env" in str(raised.value)


def test_empty_secret_is_rejected() -> None:
    with pytest.raises(CredentialError):
        SecretKey("   ")


def test_prices_load_from_the_committed_file() -> None:
    prices = Prices.load(Path("config/prices.toml"))
    assert DEFAULT_MODEL in prices.models
    assert prices.cost_usd(
        DEFAULT_MODEL,
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        at=datetime(2026, 10, 31, 12, 0, tzinfo=UTC),
    ) == pytest.approx(0.75)


def test_peak_window_and_weekend_rules() -> None:
    prices = default_prices()
    assert prices.is_peak(datetime(2026, 10, 28, 2, 0, tzinfo=UTC))
    assert not prices.is_peak(datetime(2026, 10, 28, 5, 0, tzinfo=UTC))
    assert not prices.is_peak(datetime(2026, 10, 31, 2, 0, tzinfo=UTC))  # Saturday


def test_cached_input_is_cheaper() -> None:
    prices = default_prices()
    at = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
    fresh = prices.cost_usd(
        DEFAULT_MODEL, input_tokens=1_000_000, output_tokens=0, at=at
    )
    cached = prices.cost_usd(
        DEFAULT_MODEL,
        input_tokens=1_000_000,
        output_tokens=0,
        cached_tokens=1_000_000,
        at=at,
    )
    assert cached == pytest.approx(0.003)
    assert cached < fresh


def test_budget_config_matches_plan_limits() -> None:
    config = BudgetConfig.load(Path("config/budget.toml"))
    assert (config.max_steps, config.max_tokens) == (12, 40_000)
    assert (config.pace.max_concurrent, config.pace.per_minute) == (2, 30)
    assert config.request.temperature == 0.0
    assert config.request.max_tokens >= 1024


def test_missing_config_files_use_committed_defaults(tmp_path: Path) -> None:
    config = BudgetConfig.load(tmp_path / "absent.toml")
    prices = Prices.load(tmp_path / "absent.toml")
    assert config.max_steps == 12
    assert prices.price_for(DEFAULT_MODEL).output_per_million == 0.60
