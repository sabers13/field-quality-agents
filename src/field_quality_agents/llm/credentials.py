"""Credential loading: ``FQA_ENV_FILE`` first, then ``.env``.

The value is wrapped in :class:`SecretKey`, whose ``repr`` and ``str`` are
redacted. Only :meth:`SecretKey.reveal` returns the raw string, and only the
HTTP client calls it to build an ``Authorization`` header. Nothing in this
module prints, logs or serialises a key.
"""

from __future__ import annotations

import os
from pathlib import Path

from field_quality_agents.llm.errors import CredentialError

__all__ = ["KEY_NAMES", "SecretKey", "default_env_file", "load_api_key"]

#: Names accepted inside the env file, in priority order.
KEY_NAMES: tuple[str, ...] = (
    "FQA_API_KEY",
    "OPENCODE_API_KEY",
    "OPENCODE_GO_API_KEY",
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "API_KEY",
)


class SecretKey:
    """A credential that refuses to reveal itself in text or repr."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not value.strip():
            raise CredentialError("the key file contains an empty value")
        self._value = value.strip()

    def reveal(self) -> str:
        """Return the raw value; only the HTTP client may call this."""

        return self._value

    def __repr__(self) -> str:
        return "SecretKey(<redacted>)"

    def __str__(self) -> str:
        return "<redacted>"

    def __bool__(self) -> bool:
        return True

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SecretKey):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)


def default_env_file() -> Path:
    """The PLAN §2 default when ``FQA_ENV_FILE`` is not set."""

    return Path.home() / ".config" / "field-quality-agents" / "upstream.env"


def load_api_key(
    env_file: Path | None = None,
    *,
    dotenv: Path | None = None,
) -> SecretKey:
    """Load the key from ``FQA_ENV_FILE`` (or its default), then ``.env``.

    Raises :class:`CredentialError` without echoing file contents.
    """

    candidates: list[Path] = []
    if env_file is not None:
        candidates.append(Path(env_file).expanduser())
    else:
        configured = os.environ.get("FQA_ENV_FILE")
        candidates.append(Path(configured).expanduser() if configured else default_env_file())
    candidates.append(Path(dotenv) if dotenv is not None else Path(".env"))

    for path in candidates:
        value = _read_key(path)
        if value is not None:
            return SecretKey(value)

    names = ", ".join(str(path) for path in candidates)
    raise CredentialError(
        f"no model key found; expected one of {', '.join(KEY_NAMES)} in {names}"
    )


def _read_key(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise CredentialError(f"could not read the key file at {path}") from exc

    assignments = _assignments(text)
    for name in KEY_NAMES:
        if name in assignments:
            return _clean(assignments[name])
    if len(assignments) == 1:
        # A single-assignment file is unambiguous even when the variable name
        # is not one we know; the name still never appears in an error.
        return _clean(next(iter(assignments.values())))
    return None


def _assignments(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].strip()
        if "=" not in stripped:
            continue
        name, raw = stripped.split("=", 1)
        name = name.strip()
        if not name:
            continue
        values[name.upper()] = raw
    return values


def _clean(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value.strip()
