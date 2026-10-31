#!/usr/bin/env python3
"""Lightweight project facts check.

Q11 owns the real ``project-facts.yml`` and its cross-checks against
``results/``. Until that file exists this check is deliberately a no-op so
``make release-check`` is meaningful on the Q0 scaffold.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "project-facts.yml"


def main() -> int:
    if not FACTS.exists():
        print("facts: project-facts.yml not present yet (Q11); nothing to verify")
        return 0
    text = FACTS.read_text(encoding="utf-8")
    if not text.strip():
        print("facts: FAIL project-facts.yml is empty")
        return 1
    # Full schema checks are Q11's job. Keep a guard against an obviously
    # half-written file until then.
    missing = [key for key in ("name:", "tagline:") if key not in text]
    if missing:
        print(f"facts: FAIL project-facts.yml missing keys: {', '.join(missing)}")
        return 1
    print("facts: ok (basic project-facts.yml present)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
