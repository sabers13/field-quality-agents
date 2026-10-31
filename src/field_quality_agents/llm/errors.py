"""Errors raised by the model lane.

The names in ``docs/INTERFACES.md`` are part of the contract. ``PolicyStopError``
has a side effect on purpose: PLAN §10 rule 3 says a policy or account warning
stops the run, so the error writes ``reports/STOP.md`` before the caller sees it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

__all__ = [
    "BadAnswerError",
    "CredentialError",
    "ModelError",
    "PolicyStopError",
    "RateLimitError",
    "ReplayMissError",
    "TransportError",
]


class ModelError(RuntimeError):
    """Base class for every model-lane failure."""


class CredentialError(ModelError):
    """No usable key was found. The message never contains a value."""


class TransportError(ModelError):
    """The request did not produce a usable HTTP response."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(TransportError):
    """HTTP 429 after the bounded retry budget was spent."""

    def __init__(self, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class BadAnswerError(ModelError):
    """The endpoint answered 2xx with a body that is not a valid model turn.

    A bad answer is never retried: retrying cannot make a malformed tool call
    well formed, and the agents must see the failure.
    """


class ReplayMissError(ModelError):
    """Replay was asked for a key that is not in the recording store."""

    def __init__(self, key: str) -> None:
        super().__init__(f"no recording for key {key}")
        self.key = key


class PolicyStopError(ModelError):
    """HTTP 403, an abuse/policy message or an account warning.

    PLAN §10 rule 3: write the stop report and make no further calls.
    """

    def __init__(self, reason: str, *, stop_path: Path = Path("reports/STOP.md")) -> None:
        super().__init__(f"model policy stop: {reason}")
        self.reason = reason
        self.stop_path = stop_path
        self._write_stop_report()

    def _write_stop_report(self) -> None:
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        body = (
            "\n# STOP\n\n"
            f"Model policy stop at {stamp}.\n\n"
            f"Reason: {self.reason}\n\n"
            "PLAN §10 rule 3 requires the run to stop. No further model calls "
            "were made by this client.\n"
        )
        try:
            self.stop_path.parent.mkdir(parents=True, exist_ok=True)
            with self.stop_path.open("a", encoding="utf-8") as handle:
                handle.write(body)
        except OSError:
            # The stop is still enforced in-process; a read-only checkout must
            # not turn a policy stop into a different exception.
            pass
