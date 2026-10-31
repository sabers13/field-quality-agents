"""Prompts are versioned files, and the version travels with each run."""

from __future__ import annotations

import pytest
from helpers import intake_payload, make_case, run_desk

from field_quality_agents.agents.prompts import (
    AGENTS,
    PromptNotFoundError,
    load_prompt,
)
from field_quality_agents.agents.state import PROMPT_VERSION


@pytest.mark.parametrize("agent", AGENTS)
def test_every_agent_has_a_p1_prompt(agent: str) -> None:
    text = load_prompt(agent, "p1")
    assert text
    assert "JSON" in text


def test_the_loaded_version_is_p1() -> None:
    assert PROMPT_VERSION == "p1"
    assert load_prompt("analysis") == load_prompt("analysis", "p1")


def test_a_missing_version_is_an_error() -> None:
    with pytest.raises(PromptNotFoundError):
        load_prompt("intake", "p99")


@pytest.mark.parametrize("agent", ["../escape", "Intake", "in take", ""])
def test_agent_names_cannot_escape_the_prompt_directory(agent: str) -> None:
    with pytest.raises(ValueError):
        load_prompt(agent)


@pytest.mark.parametrize("version", ["../p1", "p1/../../secret", "latest", ""])
def test_versions_must_look_like_p_number(version: str) -> None:
    with pytest.raises(ValueError):
        load_prompt("intake", version)


def test_run_records_the_prompt_version() -> None:
    run, _model, _tools = run_desk(make_case(), intake=intake_payload(missing=("mileage",)))
    assert run.prompt_version == PROMPT_VERSION
    supervisor_steps = [step for step in run.trace if step.agent == "supervisor"]
    assert supervisor_steps
    assert "p1" in supervisor_steps[0].reason
