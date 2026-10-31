#!/usr/bin/env python3
"""Fail if a tracked file or recent commit message contains a forbidden name.

Only file:line and a hash prefix are printed; the token itself is never shown.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HASH_FILE = ROOT / "config" / "forbidden.sha256"
MAX_BYTES = 8 * 1024 * 1024
TOKEN = re.compile(r"[a-z0-9][a-z0-9._+-]*")
SPLIT = re.compile(r"[._+-]+")
COMMIT_LIMIT = int(os.environ.get("FQA_FORBIDDEN_COMMITS", "50"))


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_forbidden() -> set[str]:
    if not HASH_FILE.is_file():
        raise SystemExit(f"scan-forbidden: missing {HASH_FILE}")
    hashes = {
        line.strip().lower()
        for line in HASH_FILE.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if len(hashes) != 7:
        raise SystemExit(
            f"scan-forbidden: expected exactly 7 hashes in {HASH_FILE}, found {len(hashes)}"
        )
    return hashes


def token_digests(token: str) -> Iterable[str]:
    token = token.strip("._+-")
    if not token:
        return
    yield sha256(token)
    for part in SPLIT.split(token):
        part = part.strip("._+-")
        if part:
            yield sha256(part)


def scan_text(label: str, text: str, forbidden: set[str]) -> set[tuple[str, int, str]]:
    hits: set[tuple[str, int, str]] = set()
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in TOKEN.finditer(line.lower()):
            for digest in token_digests(match.group(0)):
                if digest in forbidden:
                    hits.add((label, lineno, digest[:12]))
    return hits


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit("scan-forbidden: git ls-files failed; run inside the repository")
    return [ROOT / raw.decode() for raw in result.stdout.split(b"\x00") if raw]


def scan_files(forbidden: set[str]) -> tuple[set[tuple[str, int, str]], int]:
    hits: set[tuple[str, int, str]] = set()
    checked = 0
    for path in tracked_files():
        try:
            if not path.is_file() or path.stat().st_size > MAX_BYTES:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in data[:4096]:
            continue
        checked += 1
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("utf-8", "ignore")
        hits |= scan_text(str(path.relative_to(ROOT)), text, forbidden)
    return hits, checked


def scan_commits(forbidden: set[str]) -> tuple[set[tuple[str, int, str]], int]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "log", f"-n{COMMIT_LIMIT}", "--format=%H%x1f%B%x1e"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return set(), 0
    hits: set[tuple[str, int, str]] = set()
    count = 0
    for record in result.stdout.decode("utf-8", "ignore").split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        sha, _, body = record.partition("\x1f")
        if not sha:
            continue
        count += 1
        hits |= scan_text(f"commit:{sha[:12]}", body, forbidden)
    return hits, count


def main() -> int:
    forbidden = load_forbidden()
    file_hits, files_checked = scan_files(forbidden)
    commit_hits, commits_checked = scan_commits(forbidden)
    hits = sorted(file_hits | commit_hits)
    for label, lineno, prefix in hits:
        print(f"{label}:{lineno}: forbidden token sha256:{prefix}")
    if hits:
        print(f"scan-forbidden: FAIL ({len(hits)} hit(s))")
        return 1
    print(
        f"scan-forbidden: ok ({files_checked} tracked files, "
        f"{commits_checked} commit messages)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
