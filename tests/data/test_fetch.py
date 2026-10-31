"""Offline checks for the fetch helpers (no network)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from field_quality_agents.data.fetch import _extract, _sha256


def test_sha256_and_size(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"field-quality-agents")
    digest, size = _sha256(path)
    assert size == 20
    assert len(digest) == 64


def test_extract_zip_member(tmp_path: Path) -> None:
    archive = tmp_path / "FLAT_INV.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("FLAT_INV.txt", "one\ttwo\n")
    extracted = _extract(archive, expected="FLAT_INV.txt")
    assert extracted.name == "FLAT_INV.txt"
    assert extracted.read_text(encoding="utf-8") == "one\ttwo\n"


def test_extract_rejects_an_unexpected_member(tmp_path: Path) -> None:
    archive = tmp_path / "FLAT_INV.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("wrong.txt", "no")
    with pytest.raises(ValueError):
        _extract(archive, expected="FLAT_INV.txt")
