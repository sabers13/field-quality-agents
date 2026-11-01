#!/usr/bin/env python3
"""Write or check ``results/MANIFEST.sha256``.

PLAN §8: ``make all`` in replay mode (no key, no network) rebuilds the
dashboard data and the reproducible results byte-identically. This script
hashes exactly the files that ``make all`` regenerates:

* ``results/baseline/``;
* ``results/runs/replay/``;
* ``dist/field-quality-agents/`` (the generated dashboard data).

The record-mode run under ``results/runs/live-2025/`` needs the live
recordings to be *made*, not replayed by ``make all``, so it is deliberately
outside this manifest; ``reports/RUN.md`` records how it is checked.

Usage: ``python scripts/results_manifest.py write|check``.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "results" / "MANIFEST.sha256"
REPRODUCIBLE = (
    ROOT / "results" / "baseline",
    ROOT / "results" / "runs" / "replay",
    ROOT / "dist" / "field-quality-agents",
)


def _files() -> list[Path]:
    found: list[Path] = []
    for root in REPRODUCIBLE:
        if not root.is_dir():
            continue
        found.extend(
            path for path in root.rglob("*") if path.is_file() and path != MANIFEST
        )
    return sorted(found, key=lambda path: path.relative_to(ROOT).as_posix())


def _lines() -> list[str]:
    lines: list[str] = []
    for path in _files():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
    return lines


def write() -> int:
    lines = _lines()
    if not lines:
        print("manifest: no reproducible results; run `make all` first", file=sys.stderr)
        return 1
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"manifest: wrote {len(lines)} file hash(es) to {MANIFEST.relative_to(ROOT)}")
    return 0


def check() -> int:
    if not MANIFEST.is_file():
        print("manifest: FAIL results/MANIFEST.sha256 is missing", file=sys.stderr)
        return 1
    expected = MANIFEST.read_text(encoding="utf-8").splitlines()
    actual = _lines()
    if expected == actual:
        print(f"manifest: ok ({len(actual)} file(s) byte-identical)")
        return 0
    missing = sorted(set(expected) - set(actual))
    added = sorted(set(actual) - set(expected))
    print("manifest: FAIL the reproducible results changed", file=sys.stderr)
    for line in missing[:10]:
        print(f"manifest:   was {line}", file=sys.stderr)
    for line in added[:10]:
        print(f"manifest:   now {line}", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("write", "check"):
        print("usage: results_manifest.py write|check", file=sys.stderr)
        return 2
    return write() if argv[1] == "write" else check()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
