"""Build the committed NHTSA-derived data set.

Inputs are the raw flat files under ``data/raw``; outputs are DuckDB tables
(ignored by git) and the committed zstd parquet files under ``data/``. The
selection and sampling rules are the ones in PLAN section 5.
"""

from __future__ import annotations

import csv
import json
import math
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import cast

import duckdb

from field_quality_agents.data.groups import (
    Group,
    load_groups,
    map_component,
    prefix_index,
)
from field_quality_agents.data.pii import pii_kind, screen_counts
from field_quality_agents.data.schema import (
    copy_parquet,
    read_complaints,
    read_investigations,
    read_recalls,
)
from field_quality_agents.data.stats import render_stats

__all__ = ["DataBuild", "build_all"]

KB_LIMIT = 40_000
KB_FLOOR = 250
REPLAY_LIMIT = 600
REPLAY_SAFETY = 120
REPLAY_SAFETY_FLOOR = 5
REPLAY_FLOOR = 10
FINAL_LIMIT = 150
FINAL_FLOOR = 5
SUMMARY_MAX_CHARS = 6_000

COMPLAINT_FILE_NAMES = (
    "COMPLAINTS_RECEIVED_2020-2024.txt",
    "COMPLAINTS_RECEIVED_2025-2026.txt",
)
RECALL_FILE_NAME = "FLAT_RCL_POST_2010.txt"
INVESTIGATION_FILE_NAME = "FLAT_INV.txt"


@dataclass(frozen=True)
class DataBuild:
    snapshot: dict[str, object]
    outputs: tuple[Path, ...]
    stats: dict[str, object]


def _year_sql(column: str) -> str:
    return (
        "CASE WHEN try_cast(nullif(trim(" + column + "), '') AS INTEGER) = 9999 "
        "THEN NULL ELSE try_cast(nullif(trim(" + column + "), '') AS INTEGER) END"
    )


def _date_sql(column: str) -> str:
    return f"try_strptime(nullif(trim({column}), ''), '%Y%m%d')::DATE"


def _scalar(con: duckdb.DuckDBPyConnection, query: str, params: Sequence[object] = ()) -> int:
    row = con.execute(query, list(params)).fetchone()
    if row is None:
        return 0
    return int(row[0])


def _largest_remainder(counts: Mapping[str, int], n: int) -> dict[str, int]:
    total = sum(counts.values())
    if n <= 0 or total <= 0:
        return {}
    exact = {key: n * value / total for key, value in counts.items()}
    result = {key: math.floor(value) for key, value in exact.items()}
    left = n - sum(result.values())
    order = sorted(
        counts,
        key=lambda key: (-(exact[key] - result[key]), -counts[key], key),
    )
    for key in order:
        if left <= 0:
            break
        if result[key] < counts[key]:
            result[key] += 1
            left -= 1
    return {key: value for key, value in result.items() if value > 0}


def _quotas(counts: Mapping[str, int], n: int, floor: int) -> dict[str, int]:
    """Stratified allocation: a floor per group then proportional remainder."""
    available = {key: value for key, value in counts.items() if value > 0}
    total = sum(available.values())
    target = min(n, total)
    if target <= 0:
        return {}
    if floor * len(available) > target:
        return _largest_remainder(available, target)
    quotas = {key: min(value, floor) for key, value in available.items()}
    remaining = target - sum(quotas.values())
    caps = {key: available[key] - quotas[key] for key in available}
    while remaining > 0:
        open_groups = {key: value for key, value in caps.items() if value > 0}
        if not open_groups:
            break
        allocation = _largest_remainder(open_groups, remaining)
        moved = 0
        for key, amount in allocation.items():
            take = min(amount, caps[key])
            quotas[key] += take
            caps[key] -= take
            moved += take
        if moved == 0:
            break
        remaining -= moved
    return {key: value for key, value in quotas.items() if value > 0}


def _table_counts(
    con: duckdb.DuckDBPyConnection, table: str, where: str = ""
) -> dict[str, int]:
    rows = con.execute(
        f"SELECT group_id, count(*) FROM {table} {where} GROUP BY 1 ORDER BY 1"
    ).fetchall()
    return {str(group_id): int(count) for group_id, count in rows}


def _pick(
    con: duckdb.DuckDBPyConnection,
    candidates: str,
    quotas: Mapping[str, int],
    seed: str,
    output: str,
) -> None:
    con.execute(
        f"CREATE OR REPLACE TABLE {output} AS "
        f"SELECT id, group_id, safety_relevant, received_at FROM {candidates} WHERE FALSE"
    )
    if not quotas:
        return
    con.execute("CREATE OR REPLACE TABLE quotas(group_id VARCHAR, quota INTEGER)")
    con.executemany("INSERT INTO quotas VALUES (?, ?)", list(quotas.items()))
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {output} AS
        SELECT id, group_id, safety_relevant, received_at
        FROM (
            SELECT c.*,
                   row_number() OVER (
                       PARTITION BY group_id
                       ORDER BY md5(concat(?, ':', id)), id
                   ) AS rn
            FROM {candidates} c
        ) ranked
        JOIN quotas USING (group_id)
        WHERE ranked.rn <= quotas.quota
        """,
        [seed],
    )


def _sample_kb(con: duckdb.DuckDBPyConnection) -> None:
    counts = _table_counts(con, "candidates_kb")
    quotas = _quotas(counts, KB_LIMIT, KB_FLOOR)
    _pick(con, "candidates_kb", quotas, "20261031-kb", "picked_kb")


def _sample_replay(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        "CREATE OR REPLACE TABLE candidates_replay_safety AS "
        "SELECT * FROM candidates_replay WHERE safety_relevant"
    )
    safety_counts = _table_counts(con, "candidates_replay_safety")
    safety_target = min(REPLAY_SAFETY, sum(safety_counts.values()))
    _pick(
        con,
        "candidates_replay_safety",
        _quotas(safety_counts, safety_target, REPLAY_SAFETY_FLOOR),
        "20261031-replay-safety",
        "picked_replay_safety",
    )
    selected = _scalar(con, "SELECT count(*) FROM picked_replay_safety")
    con.execute(
        "CREATE OR REPLACE TABLE candidates_replay_rest AS "
        "SELECT * FROM candidates_replay "
        "WHERE id NOT IN (SELECT id FROM picked_replay_safety)"
    )
    rest_counts = _table_counts(con, "candidates_replay_rest")
    remaining = max(0, REPLAY_LIMIT - selected)
    _pick(
        con,
        "candidates_replay_rest",
        _quotas(rest_counts, remaining, REPLAY_FLOOR),
        "20261031-replay-rest",
        "picked_replay_rest",
    )
    con.execute(
        "CREATE OR REPLACE TABLE picked_replay AS "
        "SELECT * FROM picked_replay_safety UNION ALL SELECT * FROM picked_replay_rest"
    )


def _sample_final(con: duckdb.DuckDBPyConnection) -> None:
    counts = _table_counts(con, "candidates_final")
    _pick(
        con,
        "candidates_final",
        _quotas(counts, FINAL_LIMIT, FINAL_FLOOR),
        "20261031-final",
        "picked_final",
    )


def _final_window(max_date: date) -> tuple[date, date]:
    """The last four complete Monday-Sunday weeks before the snapshot edge."""
    days_since_sunday = (max_date.weekday() + 1) % 7
    last_sunday = max_date - timedelta(days=days_since_sunday)
    if last_sunday == max_date:
        last_sunday -= timedelta(days=7)
    return last_sunday - timedelta(days=27), last_sunday


def _load_snapshot(out_dir: Path) -> dict[str, object]:
    path = out_dir / "SNAPSHOT.json"
    if not path.is_file():
        return {}
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _read_raw(con: duckdb.DuckDBPyConnection, raw_dir: Path) -> None:
    complaint_paths = [raw_dir / name for name in COMPLAINT_FILE_NAMES]
    for path in complaint_paths:
        if not path.is_file():
            raise FileNotFoundError(
                f"{path} is missing; run 'fqa data --refresh' or 'make fetch-data' first"
            )
    recall_path = raw_dir / RECALL_FILE_NAME
    investigation_path = raw_dir / INVESTIGATION_FILE_NAME
    if not recall_path.is_file():
        raise FileNotFoundError(f"{recall_path} is missing; run the data fetch first")
    if not investigation_path.is_file():
        raise FileNotFoundError(
            f"{investigation_path} is missing; run the data fetch first"
        )
    read_complaints(con, complaint_paths)
    read_recalls(con, recall_path)
    read_investigations(con, investigation_path)


def _build_component_map(
    con: duckdb.DuckDBPyConnection, groups: Mapping[str, Group]
) -> dict[str, object]:
    con.execute(
        """
        CREATE OR REPLACE TABLE component_values AS
        SELECT DISTINCT trim(COALESCE(COMPDESC, '')) AS component FROM complaints_raw
        UNION
        SELECT DISTINCT trim(COALESCE(COMPNAME, '')) AS component FROM recalls_raw
        UNION
        SELECT DISTINCT trim(COALESCE(COMPNAME, '')) AS component
        FROM investigations_raw
        """
    )
    rows = con.execute(
        "SELECT component FROM component_values WHERE component <> '' ORDER BY component"
    ).fetchall()
    index = prefix_index(groups)
    mapping = [
        (str(component), map_component(str(component), index)) for (component,) in rows
    ]
    con.execute(
        "CREATE OR REPLACE TABLE component_map(component VARCHAR, group_id VARCHAR)"
    )
    con.executemany("INSERT INTO component_map VALUES (?, ?)", mapping)
    mapped = sum(1 for _, group_id in mapping if group_id is not None)
    return {
        "distinct_component_values": len(mapping),
        "mapped_component_values": mapped,
        "unmapped_component_values": len(mapping) - mapped,
    }


def _build_complaints(con: duckdb.DuckDBPyConnection, out_dir: Path) -> dict[str, object]:
    con.execute(
        """
        CREATE OR REPLACE TABLE complaint_components AS
        SELECT CMPLID AS id,
               list_sort(list(DISTINCT trim(COALESCE(COMPDESC, '')))) AS components
        FROM complaints_raw
        GROUP BY CMPLID
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE complaint_component_rows AS
        SELECT id, unnest(components) AS component FROM complaint_components
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE complaint_products AS
        SELECT CMPLID AS id,
               count(DISTINCT (
                   upper(trim(COALESCE(MAKETXT, ''))) || '|' ||
                   upper(trim(COALESCE(MODELTXT, ''))) || '|' ||
                   trim(COALESCE(YEARTXT, ''))
               )) AS n_products
        FROM complaints_raw
        GROUP BY CMPLID
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE complaint_core AS
        SELECT
            CMPLID AS id,
            min({_date_sql("LDATE")}) AS received_at,
            min(upper(trim(COALESCE(MAKETXT, '')))) AS make,
            min(upper(trim(COALESCE(MODELTXT, '')))) AS model,
            min({_year_sql("YEARTXT")}) AS year,
            min(trim(COALESCE(CDESCR, ''))) AS narrative,
            bool_or(
                upper(trim(COALESCE(CRASH, ''))) = 'Y'
                OR upper(trim(COALESCE(FIRE, ''))) = 'Y'
                OR COALESCE(try_cast(nullif(trim(INJURED), '') AS INTEGER), 0) > 0
                OR COALESCE(try_cast(nullif(trim(DEATHS), '') AS INTEGER), 0) > 0
            ) AS safety_relevant,
            min(try_cast(nullif(trim(MILES), '') AS INTEGER)) AS mileage
        FROM complaints_raw
        GROUP BY CMPLID
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE complaint_base AS
        SELECT c.*
        FROM complaint_core c
        JOIN complaint_products p USING (id)
        WHERE p.n_products = 1
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE complaint_group_check AS
        SELECT r.id,
               count(*) AS n_components,
               count(m.group_id) AS n_mapped,
               count(DISTINCT m.group_id) AS n_groups,
               min(m.group_id) AS group_id
        FROM complaint_component_rows r
        LEFT JOIN component_map m USING (component)
        GROUP BY r.id
        HAVING count(*) = count(m.group_id) AND count(DISTINCT m.group_id) = 1
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE complaints_mapped AS
        SELECT b.id,
               b.received_at,
               b.make,
               b.model,
               b.year,
               cc.components[1] AS component,
               g.group_id,
               b.narrative,
               b.safety_relevant,
               b.mileage
        FROM complaint_base b
        JOIN complaint_group_check g USING (id)
        JOIN complaint_components cc USING (id)
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE complaints_long AS
        SELECT * FROM complaints_mapped
        WHERE length(trim(narrative)) >= 80
        """
    )
    rows = con.execute(
        "SELECT id, narrative FROM complaints_long ORDER BY id"
    ).fetchall()
    screened = [(str(cid), pii_kind(str(text))) for cid, text in rows]
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".pii_screen_", suffix=".tsv", dir=out_dir
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(
                handle,
                delimiter="\t",
                lineterminator="\n",
                quoting=csv.QUOTE_NONE,
                escapechar="\\",
            )
            for case_id, kind in screened:
                writer.writerow([case_id, kind or ""])
        con.execute(
            """
            CREATE OR REPLACE TABLE pii_screen AS
            SELECT column0 AS id, nullif(column1, '') AS pii_kind
            FROM read_csv(
                ?,
                columns={'column0': 'VARCHAR', 'column1': 'VARCHAR'},
                delim='\t', header=false, auto_detect=false, quote=''
            )
            """,
            [str(temporary)],
        )
    finally:
        temporary.unlink(missing_ok=True)
    con.execute(
        """
        CREATE OR REPLACE TABLE complaints_clean AS
        SELECT c.*
        FROM complaints_long c
        LEFT JOIN pii_screen p USING (id)
        WHERE p.pii_kind IS NULL
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE complaints_eligible AS
        SELECT * FROM complaints_clean
        WHERE make <> '' AND model <> '' AND year IS NOT NULL
        """
    )
    counts = screen_counts(str(text) for _, text in rows)
    total = _scalar(con, "SELECT count(*) FROM complaints_raw")
    distinct = _scalar(con, "SELECT count(*) FROM complaint_core")
    multi_product = int(
        con.execute(
            "SELECT count(*) FROM complaint_products WHERE n_products > 1"
        ).fetchone()[0]  # type: ignore[index]
    )
    single_group = _scalar(con, "SELECT count(*) FROM complaint_group_check")
    mapped = _scalar(con, "SELECT count(*) FROM complaints_mapped")
    long_rows = _scalar(con, "SELECT count(*) FROM complaints_long")
    clean = _scalar(con, "SELECT count(*) FROM complaints_clean")
    eligible = _scalar(con, "SELECT count(*) FROM complaints_eligible")
    return {
        "rows_read": total,
        "distinct_complaints": distinct,
        "multi_product_dropped": multi_product,
        "single_group_complaints": single_group,
        "mapped_complaints": mapped,
        "narrative_under_80_dropped": mapped - long_rows,
        "pii_screen": counts,
        "pii_dropped": long_rows - clean,
        "missing_product_key_dropped": clean - eligible,
        "eligible_complaints": eligible,
    }


def _build_events(con: duckdb.DuckDBPyConnection) -> dict[str, object]:
    con.execute(
        f"""
        CREATE OR REPLACE TABLE recalls_staged AS
        SELECT
            trim(COALESCE(CAMPNO, '')) AS id,
            upper(trim(COALESCE(MAKETXT, ''))) AS make,
            upper(trim(COALESCE(MODELTXT, ''))) AS model,
            {_year_sql("YEARTXT")} AS year,
            trim(COALESCE(COMPNAME, '')) AS component,
            min(m.group_id) AS group_id,
            min(trim(COALESCE(DESC_DEFECT, ''))) AS summary,
            min(COALESCE(
                {_date_sql("RCDATE")}, {_date_sql("DATEA")}, {_date_sql("ODATE")}
            )) AS open_date
        FROM recalls_raw r
        LEFT JOIN component_map m
            ON trim(COALESCE(r.COMPNAME, '')) = m.component
        GROUP BY 1, 2, 3, 4, 5
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE recalls_out AS
        SELECT id, make, model, year, component, group_id AS "group",
               left(summary, {SUMMARY_MAX_CHARS}) AS summary, open_date
        FROM recalls_staged
        WHERE id <> '' AND open_date IS NOT NULL
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE investigations_staged AS
        SELECT
            trim(COALESCE(NHTSA_ACTION_NUMBER, '')) AS id,
            upper(trim(COALESCE(MAKE, ''))) AS make,
            upper(trim(COALESCE(MODEL, ''))) AS model,
            {_year_sql("YEAR")} AS year,
            trim(COALESCE(COMPNAME, '')) AS component,
            min(m.group_id) AS group_id,
            min(trim(COALESCE(SUMMARY, ''))) AS summary,
            min({_date_sql("ODATE")}) AS open_date
        FROM investigations_raw i
        LEFT JOIN component_map m
            ON trim(COALESCE(i.COMPNAME, '')) = m.component
        GROUP BY 1, 2, 3, 4, 5
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE investigations_out AS
        SELECT id, make, model, year, component, group_id AS "group",
               left(summary, {SUMMARY_MAX_CHARS}) AS summary, open_date
        FROM investigations_staged
        WHERE id <> '' AND open_date IS NOT NULL
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE events_out AS
        SELECT DISTINCT make, model, year, "group", 'recall' AS event_type,
               open_date AS event_date, id AS source_id
        FROM recalls_out
        WHERE "group" IS NOT NULL AND year IS NOT NULL
        UNION
        SELECT DISTINCT make, model, year, "group", 'investigation' AS event_type,
               open_date AS event_date, id AS source_id
        FROM investigations_out
        WHERE "group" IS NOT NULL AND year IS NOT NULL
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE fleet_weekly_out AS
        SELECT date_trunc('week', received_at)::DATE AS week_start,
               make, model, year, group_id AS "group", count(*) AS count
        FROM complaints_mapped
        WHERE received_at IS NOT NULL
          AND make <> '' AND model <> '' AND year IS NOT NULL
        GROUP BY 1, 2, 3, 4, 5
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE fleet_keys AS
        SELECT DISTINCT make, model, year, "group" FROM fleet_weekly_out
        """
    )
    recall_rows = _scalar(con, "SELECT count(*) FROM recalls_raw")
    recall_campaigns = int(
        con.execute(
            "SELECT count(DISTINCT CAMPNO) FROM recalls_raw WHERE trim(COALESCE(CAMPNO, '')) <> ''"
        ).fetchone()[0]  # type: ignore[index]
    )
    recall_mapped_rows = int(
        con.execute(
            "SELECT count(*) FROM recalls_raw r JOIN component_map m "
            "ON trim(COALESCE(r.COMPNAME, '')) = m.component "
            "WHERE m.group_id IS NOT NULL"
        ).fetchone()[0]  # type: ignore[index]
    )
    recall_mapped_campaigns = int(
        con.execute(
            "SELECT count(DISTINCT r.CAMPNO) FROM recalls_raw r "
            "JOIN component_map m ON trim(COALESCE(r.COMPNAME, '')) = m.component "
            "WHERE trim(COALESCE(r.CAMPNO, '')) <> '' AND m.group_id IS NOT NULL"
        ).fetchone()[0]  # type: ignore[index]
    )
    investigation_rows = _scalar(con, "SELECT count(*) FROM investigations_raw")
    investigation_actions = int(
        con.execute(
            "SELECT count(DISTINCT NHTSA_ACTION_NUMBER) FROM investigations_raw "
            "WHERE trim(COALESCE(NHTSA_ACTION_NUMBER, '')) <> ''"
        ).fetchone()[0]  # type: ignore[index]
    )
    investigation_mapped_rows = int(
        con.execute(
            "SELECT count(*) FROM investigations_raw i JOIN component_map m "
            "ON trim(COALESCE(i.COMPNAME, '')) = m.component "
            "WHERE m.group_id IS NOT NULL"
        ).fetchone()[0]  # type: ignore[index]
    )
    investigation_mapped_actions = int(
        con.execute(
            "SELECT count(DISTINCT i.NHTSA_ACTION_NUMBER) FROM investigations_raw i "
            "JOIN component_map m ON trim(COALESCE(i.COMPNAME, '')) = m.component "
            "WHERE trim(COALESCE(i.NHTSA_ACTION_NUMBER, '')) <> '' "
            "AND m.group_id IS NOT NULL"
        ).fetchone()[0]  # type: ignore[index]
    )
    event_rows = _scalar(con, "SELECT count(*) FROM events_out")
    event_joined = int(
        con.execute(
            "SELECT count(*) FROM events_out e JOIN fleet_keys f "
            'ON e.make = f.make AND e.model = f.model AND e.year = f.year '
            'AND e."group" = f."group"'
        ).fetchone()[0]  # type: ignore[index]
    )
    return {
        "recalls": {
            "rows_read": recall_rows,
            "campaigns": recall_campaigns,
            "mapped_rows": recall_mapped_rows,
            "mapped_campaigns": recall_mapped_campaigns,
            "output_rows": _scalar(con, "SELECT count(*) FROM recalls_out"),
        },
        "investigations": {
            "rows_read": investigation_rows,
            "actions": investigation_actions,
            "mapped_rows": investigation_mapped_rows,
            "mapped_actions": investigation_mapped_actions,
            "output_rows": _scalar(con, "SELECT count(*) FROM investigations_out"),
        },
        "events": {
            "rows": event_rows,
            "joined_to_fleet": event_joined,
            "recalls": int(
                con.execute(
                    "SELECT count(*) FROM events_out WHERE event_type = 'recall'"
                ).fetchone()[0]  # type: ignore[index]
            ),
            "investigations": int(
                con.execute(
                    "SELECT count(*) FROM events_out WHERE event_type = 'investigation'"
                ).fetchone()[0]  # type: ignore[index]
            ),
        },
    }


def _set_stats(
    con: duckdb.DuckDBPyConnection,
    picked: str,
    label: str,
    group_ids: Sequence[str],
) -> dict[str, object]:
    rows = con.execute(
        f"""
        SELECT p.group_id,
               count(*) AS n,
               count(*) FILTER (WHERE e.safety_relevant) AS safety
        FROM {picked} p
        JOIN complaints_eligible e USING (id)
        GROUP BY p.group_id
        ORDER BY p.group_id
        """
    ).fetchall()
    counts = {str(group_id): int(n) for group_id, n, _ in rows}
    safety = {str(group_id): int(s) for group_id, _, s in rows}
    total = sum(counts.values())
    safety_total = sum(safety.values())
    return {
        "label": label,
        "rows": total,
        "safety_relevant": safety_total,
        "safety_rate": (safety_total / total) if total else 0.0,
        "by_group": {
            group_id: {
                "rows": counts.get(group_id, 0),
                "safety_relevant": safety.get(group_id, 0),
            }
            for group_id in group_ids
        },
    }


def _write_outputs(
    con: duckdb.DuckDBPyConnection, out_dir: Path
) -> tuple[Path, ...]:
    outputs: list[Path] = []

    def write(name: str, query: str) -> None:
        path = out_dir / name
        copy_parquet(con, query, path)
        outputs.append(path)

    write(
        "kb_complaints.parquet",
        """
        SELECT e.id, e.received_at, e.make, e.model, e.year, e.component,
               e.group_id AS "group", e.narrative, e.safety_relevant, e.mileage
        FROM complaints_eligible e JOIN picked_kb p USING (id)
        ORDER BY e.id
        """,
    )
    write(
        "recalls.parquet",
        """
        SELECT id, make, model, year, component, "group", summary, open_date
        FROM recalls_out
        ORDER BY id, make, model, year, component
        """,
    )
    write(
        "investigations.parquet",
        """
        SELECT id, make, model, year, component, "group", summary, open_date
        FROM investigations_out
        ORDER BY id, make, model, year, component
        """,
    )
    write(
        "replay_2025.parquet",
        """
        SELECT e.id, e.received_at, e.make, e.model, e.year, e.component,
               e.group_id AS "group", e.narrative, e.safety_relevant, e.mileage
        FROM complaints_eligible e JOIN picked_replay p USING (id)
        ORDER BY e.received_at, e.id
        """,
    )
    write(
        "final_live.parquet",
        """
        SELECT e.id, e.received_at, e.make, e.model, e.year, e.component,
               e.group_id AS "group", e.narrative, e.safety_relevant, e.mileage
        FROM complaints_eligible e JOIN picked_final p USING (id)
        ORDER BY e.received_at, e.id
        """,
    )
    write(
        "fleet_weekly.parquet",
        """
        SELECT week_start, make, model, year, "group", count
        FROM fleet_weekly_out
        ORDER BY week_start, make, model, year, "group"
        """,
    )
    write(
        "events.parquet",
        """
        SELECT make, model, year, "group", event_type, event_date, source_id
        FROM events_out
        ORDER BY event_type, event_date, make, model, year, "group", source_id
        """,
    )
    return tuple(outputs)


def _file_stats(con: duckdb.DuckDBPyConnection, paths: Sequence[Path]) -> dict[str, object]:
    files: dict[str, object] = {}
    for path in paths:
        rows = int(
            con.execute("SELECT count(*) FROM read_parquet(?)", [str(path)]).fetchone()[0]  # type: ignore[index]
        )
        files[path.name] = {"rows": rows, "bytes": path.stat().st_size}
    return files


def _as_file_bytes(value: object) -> int:
    if isinstance(value, dict):
        size = value.get("bytes")
        if isinstance(size, int):
            return size
    return 0


def _group_table(
    con: duckdb.DuckDBPyConnection,
    groups: Mapping[str, Group],
    kb: Mapping[str, object],
    replay: Mapping[str, object],
    final: Mapping[str, object],
) -> dict[str, object]:
    all_rows = con.execute(
        """
        SELECT group_id, count(*) AS n,
               count(*) FILTER (WHERE safety_relevant) AS safety
        FROM complaints_mapped GROUP BY group_id ORDER BY group_id
        """
    ).fetchall()
    all_counts = {str(group_id): int(n) for group_id, n, _ in all_rows}
    all_safety = {str(group_id): int(s) for group_id, _, s in all_rows}
    fleet_rows = con.execute(
        'SELECT "group", sum(count) FROM fleet_weekly_out GROUP BY 1 ORDER BY 1'
    ).fetchall()
    fleet_counts = {str(group_id): int(n) for group_id, n in fleet_rows}
    kb_groups = kb["by_group"]
    replay_groups = replay["by_group"]
    final_groups = final["by_group"]
    kb_groups = cast(dict[str, dict[str, int]], kb_groups)
    replay_groups = cast(dict[str, dict[str, int]], replay_groups)
    final_groups = cast(dict[str, dict[str, int]], final_groups)
    table: dict[str, object] = {}
    for group_id in groups:
        total = all_counts.get(group_id, 0)
        safety = all_safety.get(group_id, 0)
        kb_item = kb_groups.get(group_id, {"rows": 0, "safety_relevant": 0})
        replay_item = replay_groups.get(group_id, {"rows": 0, "safety_relevant": 0})
        final_item = final_groups.get(group_id, {"rows": 0, "safety_relevant": 0})
        table[group_id] = {
            "complaints": total,
            "safety_relevant": safety,
            "safety_rate": (safety / total) if total else 0.0,
            "kb": int(kb_item["rows"]),
            "kb_safety_relevant": int(kb_item["safety_relevant"]),
            "replay": int(replay_item["rows"]),
            "replay_safety_relevant": int(replay_item["safety_relevant"]),
            "final": int(final_item["rows"]),
            "fleet_weekly_cases": fleet_counts.get(group_id, 0),
        }
    return table


def build_all(
    raw_dir: Path = Path("data/raw"), out_dir: Path = Path("data")
) -> DataBuild:
    """Build every committed derived file from the raw snapshot."""
    out_dir.mkdir(parents=True, exist_ok=True)
    groups_path = out_dir / "groups.toml"
    if not groups_path.is_file():
        groups_path = Path("data/groups.toml")
    groups = load_groups(groups_path)
    snapshot = _load_snapshot(out_dir)

    db_path = out_dir / "field_quality.duckdb"
    con = duckdb.connect(str(db_path))
    try:
        con.execute("SET threads = 1")
        con.execute("SET preserve_insertion_order = true")
        con.execute("SET timezone = 'UTC'")

        _read_raw(con, raw_dir)
        component_stats = _build_component_map(con, groups)
        complaint_stats = _build_complaints(con, out_dir)
        event_stats = _build_events(con)

        max_row = con.execute(
            "SELECT max(received_at) FROM complaints_mapped"
        ).fetchone()
        max_date: date | None = max_row[0] if max_row else None
        if max_date is None:
            raise RuntimeError("no complaint has a valid received date")

        con.execute(
            """
            CREATE OR REPLACE TABLE candidates_all AS
            SELECT id, group_id, safety_relevant, received_at
            FROM complaints_eligible
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE candidates_kb AS
            SELECT * FROM candidates_all
            WHERE received_at BETWEEN DATE '2020-01-01' AND DATE '2024-12-31'
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE candidates_replay AS
            SELECT * FROM candidates_all
            WHERE received_at BETWEEN DATE '2025-01-01' AND DATE '2025-12-31'
            """
        )
        final_start, final_end = _final_window(max_date)
        con.execute(
            """
            CREATE OR REPLACE TABLE candidates_final AS
            SELECT * FROM candidates_all WHERE received_at BETWEEN ? AND ?
            """,
            [final_start, final_end],
        )

        _sample_kb(con)
        _sample_replay(con)
        _sample_final(con)

        outputs = _write_outputs(con, out_dir)

        group_ids = list(groups)
        kb_stats = _set_stats(con, "picked_kb", "knowledge base", group_ids)
        replay_stats = _set_stats(con, "picked_replay", "replay 2025", group_ids)
        final_stats = _set_stats(con, "picked_final", "final live", group_ids)
        group_table = _group_table(con, groups, kb_stats, replay_stats, final_stats)
        files = _file_stats(con, outputs)

        final_rows = _scalar(con, "SELECT count(*) FROM picked_final")
        committed_bytes = sum(
            _as_file_bytes(value) for value in files.values()
        )
        if committed_bytes > 60 * 1024 * 1024:
            raise RuntimeError(
                "committed derived data exceeds 60 MB "
                f"({committed_bytes} bytes); tighten summary caps or sampling"
            )
        stats: dict[str, object] = {
            "snapshot_max_date": max_date.isoformat(),
            "summary_max_chars": SUMMARY_MAX_CHARS,
            "groups_path": str(groups_path),
            "group_descriptions": {
                group_id: group.description for group_id, group in groups.items()
            },
            "components": component_stats,
            "complaints": complaint_stats,
            "sets": {
                "kb": kb_stats,
                "replay": replay_stats,
                "final": final_stats,
            },
            "final_window": {
                "start": final_start.isoformat(),
                "end": final_end.isoformat(),
                "rows": final_rows,
                "sealed": True,
            },
            "group_table": group_table,
            **event_stats,
            "files": files,
        }
        stats_path = out_dir / "STATS.md"
        stats_path.write_text(render_stats(stats, snapshot), encoding="utf-8")
        outputs = (*outputs, stats_path)
        return DataBuild(snapshot=snapshot, outputs=outputs, stats=stats)
    finally:
        con.close()


