#!/usr/bin/env python3
"""Download the public NHTSA flat files used by the project.

Example:
    uv run python scripts/fetch_nhtsa.py --dest data/raw --force

The script records sha256, size, Last-Modified and download time in
``data/SNAPSHOT.json``. Raw files stay under the git-ignored ``data/raw/``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from field_quality_agents.data.fetch import fetch_nhtsa


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", default="data/raw", help="raw data directory")
    parser.add_argument("--force", action="store_true", help="re-download all files")
    args = parser.parse_args(argv)

    files = fetch_nhtsa(Path(args.dest), force=args.force)
    print(f"fetched {len(files)} file(s) into {args.dest}")
    for item in files:
        print(f"  {item.name}: {item.size_bytes} bytes sha256:{item.sha256[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
