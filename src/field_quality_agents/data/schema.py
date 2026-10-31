"""Raw NHTSA flat-file schemas and TSV readers.

The NHTSA files have no header row: the column order below comes from the
published layout files (``cmpl/CMPL.txt``, ``rcl/RCL.txt``, ``inv/INV.txt``)
and is frozen in this module for the snapshot. Unknown extra fields are a
parse error rather than a silent column shift.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

import duckdb

__all__ = [
    "COMPLAINT_COLUMNS",
    "INVESTIGATION_COLUMNS",
    "RECALL_COLUMNS",
    "copy_parquet",
    "read_complaints",
    "read_investigations",
    "read_recalls",
]

COMPLAINT_COLUMNS: tuple[str, ...] = (
    "CMPLID",
    "ODINO",
    "MFR_NAME",
    "MAKETXT",
    "MODELTXT",
    "YEARTXT",
    "CRASH",
    "FAILDATE",
    "FIRE",
    "INJURED",
    "DEATHS",
    "COMPDESC",
    "CITY",
    "STATE",
    "VIN",
    "DATEA",
    "LDATE",
    "MILES",
    "OCCURENCES",
    "CDESCR",
    "CMPL_TYPE",
    "POLICE_RPT_YN",
    "PURCH_DT",
    "ORIG_OWNER_YN",
    "ANTI_BRAKES_YN",
    "CRUISE_CONT_YN",
    "NUM_CYLS",
    "DRIVE_TRAIN",
    "FUEL_SYS",
    "FUEL_TYPE",
    "TRANS_TYPE",
    "VEH_SPEED",
    "DOT",
    "TIRE_SIZE",
    "LOC_OF_TIRE",
    "TIRE_FAIL_TYPE",
    "ORIG_EQUIP_YN",
    "MANUF_DT",
    "SEAT_TYPE",
    "RESTRAINT_TYPE",
    "DEALER_NAME",
    "DEALER_TEL",
    "DEALER_CITY",
    "DEALER_STATE",
    "DEALER_ZIP",
    "PROD_TYPE",
    "REPAIRED_YN",
    "MEDICAL_ATTN",
    "VEHICLES_TOWED_YN",
    "STATE_OF_INCIDENT",
    "VEHICLE_OPERATOR",
)

RECALL_COLUMNS: tuple[str, ...] = (
    "RECORD_ID",
    "CAMPNO",
    "MAKETXT",
    "MODELTXT",
    "YEARTXT",
    "MFGCAMPNO",
    "COMPNAME",
    "MFGNAME",
    "BGMAN",
    "ENDMAN",
    "RCLTYPECD",
    "POTAFF",
    "ODATE",
    "INFLUENCED_BY",
    "MFGTXT",
    "RCDATE",
    "DATEA",
    "RPNO",
    "FMVSS",
    "DESC_DEFECT",
    "CONEQUENCE_DEFECT",
    "CORRECTIVE_ACTION",
    "NOTES",
    "RCL_CMPT_ID",
    "MFR_COMP_NAME",
    "MFR_COMP_DESC",
    "MFR_COMP_PTNO",
    "DO_NOT_DRIVE",
    "PARK_OUTSIDE",
)

INVESTIGATION_COLUMNS: tuple[str, ...] = (
    "NHTSA_ACTION_NUMBER",
    "MAKE",
    "MODEL",
    "YEAR",
    "COMPNAME",
    "MFR_NAME",
    "ODATE",
    "CDATE",
    "CAMPNO",
    "SUBJECT",
    "SUMMARY",
)


def _columns_literal(columns: Sequence[str]) -> str:
    pairs = ", ".join(f"'{name}': 'VARCHAR'" for name in columns)
    return "{" + pairs + "}"


def _read_union(
    con: duckdb.DuckDBPyConnection,
    paths: Sequence[Path],
    columns: Sequence[str],
    table: str,
) -> None:
    literal = _columns_literal(columns)
    selects = [
        (
            "SELECT * FROM read_csv(?, "
            f"columns={literal}, delim='\\t', header=false, auto_detect=false, "
            "quote='', null_padding=false, max_line_size=10000000)"
        )
        for _ in paths
    ]
    con.execute(
        f"CREATE OR REPLACE TABLE {table} AS " + " UNION ALL ".join(selects),
        [str(path) for path in paths],
    )


def read_complaints(con: duckdb.DuckDBPyConnection, paths: Sequence[Path]) -> None:
    _read_union(con, paths, COMPLAINT_COLUMNS, "complaints_raw")


def read_recalls(con: duckdb.DuckDBPyConnection, path: Path) -> None:
    _read_union(con, [path], RECALL_COLUMNS, "recalls_raw")


def read_investigations(con: duckdb.DuckDBPyConnection, path: Path) -> None:
    _read_union(con, [path], INVESTIGATION_COLUMNS, "investigations_raw")


def copy_parquet(con: duckdb.DuckDBPyConnection, query: str, path: Path) -> None:
    """Write a sorted query to parquet with zstd, atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    con.execute(
        "COPY (" + query + ") TO ? "
        "(FORMAT parquet, COMPRESSION zstd, COMPRESSION_LEVEL 15, "
        "ROW_GROUP_SIZE 100000)",
        [str(temporary)],
    )
    os.replace(temporary, path)
