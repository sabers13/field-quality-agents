"""Check the committed data files before `make all` rebuilds results.

This is the cheap first step of `make all`: it reads the parquet files and the
snapshot, prints the row counts, and fails loudly when a committed file is
missing or unreadable. It never downloads anything.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

DATA = Path("data")
PARQUET = (
    "kb_complaints.parquet",
    "recalls.parquet",
    "investigations.parquet",
    "replay_2025.parquet",
    "final_live.parquet",
    "fleet_weekly.parquet",
    "events.parquet",
)


def main() -> int:
    missing = [name for name in PARQUET if not (DATA / name).is_file()]
    snapshot = DATA / "SNAPSHOT.json"
    if not snapshot.is_file():
        missing.append("SNAPSHOT.json")
    if missing:
        print(f"data-check: missing {', '.join(missing)}", file=sys.stderr)
        return 1
    try:
        snapshot_payload = json.loads(snapshot.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"data-check: cannot read SNAPSHOT.json: {exc}", file=sys.stderr)
        return 1
    connection = duckdb.connect(":memory:")
    connection.execute("SET threads = 1")
    try:
        counts: dict[str, int] = {}
        for name in PARQUET:
            row = connection.execute(
                f"SELECT count(*) FROM read_parquet('{DATA / name}')"
            ).fetchone()
            counts[name] = int(row[0]) if row else 0
    finally:
        connection.close()
    for name, count in counts.items():
        print(f"data-check: {name} {count} row(s)")
    sources = snapshot_payload.get("sources", [])
    if isinstance(sources, list):
        print(f"data-check: snapshot lists {len(sources)} source file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
