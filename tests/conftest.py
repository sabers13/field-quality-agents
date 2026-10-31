"""Test configuration: every test runs with outbound sockets blocked."""

from __future__ import annotations

import socket
from collections.abc import Iterator
from unittest import mock

import pytest

_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
_real_getaddrinfo = socket.getaddrinfo


def _blocked_connect(self: socket.socket, address: object) -> None:
    if self.family == socket.AF_UNIX:
        _real_connect(self, address)  # type: ignore[arg-type]
        return
    raise RuntimeError(f"network access is blocked during tests (connect {address!r})")


def _blocked_connect_ex(self: socket.socket, address: object) -> int:
    if self.family == socket.AF_UNIX:
        return _real_connect_ex(self, address)  # type: ignore[arg-type]
    raise RuntimeError(f"network access is blocked during tests (connect_ex {address!r})")


def _blocked_getaddrinfo(*args: object, **kwargs: object) -> list[tuple[object, ...]]:
    raise RuntimeError("DNS/network access is blocked during tests")


@pytest.fixture(autouse=True, scope="session")
def _network_guard() -> Iterator[None]:
    with (
        mock.patch.object(socket.socket, "connect", _blocked_connect),
        mock.patch.object(socket.socket, "connect_ex", _blocked_connect_ex),
        mock.patch.object(socket, "getaddrinfo", _blocked_getaddrinfo),
    ):
        yield
