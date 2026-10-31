#!/usr/bin/env python3
"""Fail if a tracked file or recent commit message looks like it contains a secret.

The scanner reports only the file, line and pattern name; it never prints the
matched value. Credential files (``.env``) are rejected by name.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 8 * 1024 * 1024
COMMIT_LIMIT = int(os.environ.get("FQA_SECRET_COMMITS", "50"))

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("opencode-key", re.compile(r"\boc_sk_[A-Za-z0-9_\-]{20,}\b")),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b")),
    ("google-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b")),
    ("bearer-token", re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{24,}\b")),
    (
        "assigned-secret",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|token|password|passwd|client[_-]?secret)\b"
            r"\s*[:=]\s*[\"']?[A-Za-z0-9_./+=\-]{16,}"
        ),
    ),
)


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit("scan-secrets: git ls-files failed; run inside the repository")
    return [ROOT / raw.decode() for raw in result.stdout.split(b"\x00") if raw]


def scan_text(label: str, text: str) -> set[tuple[str, int, str]]:
    hits: set[tuple[str, int, str]] = set()
    for lineno, line in enumerate(text.splitlines(), start=1):
        for name, pattern in PATTERNS:
            if pattern.search(line):
                hits.add((label, lineno, name))
    return hits


def main() -> int:
    hits: set[tuple[str, int, str]] = set()
    files_checked = 0
    env_files: list[str] = []

    for path in tracked_files():
        rel = str(path.relative_to(ROOT))
        if path.name == ".env" or path.name.endswith(".env"):
            env_files.append(rel)
        try:
            if not path.is_file() or path.stat().st_size > MAX_BYTES:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in data[:4096]:
            continue
        files_checked += 1
        hits |= scan_text(rel, data.decode("utf-8", "ignore"))

    result = subprocess.run(
        ["git", "-C", str(ROOT), "log", f"-n{COMMIT_LIMIT}", "--format=%H%x1f%B%x1e"],
        check=False,
        capture_output=True,
    )
    commits_checked = 0
    if result.returncode == 0:
        for record in result.stdout.decode("utf-8", "ignore").split("\x1e"):
            record = record.strip("\n")
            if not record:
                continue
            sha, _, body = record.partition("\x1f")
            if not sha:
                continue
            commits_checked += 1
            hits |= scan_text(f"commit:{sha[:12]}", body)

    for rel in env_files:
        print(f"{rel}:0: tracked-env-file")
    for label, lineno, name in sorted(hits):
        print(f"{label}:{lineno}: {name}")

    if hits or env_files:
        print(f"scan-secrets: FAIL ({len(hits) + len(env_files)} hit(s))")
        return 1
    print(
        f"scan-secrets: ok ({files_checked} tracked files, "
        f"{commits_checked} commit messages)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
