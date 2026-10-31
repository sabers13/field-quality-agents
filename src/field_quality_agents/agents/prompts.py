"""Versioned prompt files.

Every prompt is a file under ``prompts/<agent>/<version>.md`` so a recording can
name the exact text that produced it. The version string travels in
``CaseRun.prompt_version`` and is repeated in supervisor trace reasons.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

from field_quality_agents.agents.state import PROMPT_VERSION

AGENTS = ("supervisor", "intake", "analysis")

PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"

_AGENT_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_VERSION_PATTERN = re.compile(r"^p[0-9]+$")


class PromptNotFoundError(LookupError):
    """No prompt file exists for that agent and version."""


@cache
def load_prompt(agent: str, version: str = PROMPT_VERSION) -> str:
    """Return the text of a versioned prompt.

    Names are validated so a caller cannot walk outside ``prompts/``.
    """

    if not _AGENT_PATTERN.fullmatch(agent):
        raise ValueError(f"invalid agent name: {agent!r}")
    if not _VERSION_PATTERN.fullmatch(version):
        raise ValueError(f"invalid prompt version: {version!r}")
    path = PROMPTS_DIR / agent / f"{version}.md"
    if not path.is_file():
        raise PromptNotFoundError(f"missing prompt: {agent}/{version}")
    return path.read_text(encoding="utf-8").strip()
