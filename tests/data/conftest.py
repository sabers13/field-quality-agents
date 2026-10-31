"""Fixtures for the Q1 data tests: tiny synthetic NHTSA flat files."""

from __future__ import annotations

import shutil
from collections.abc import Iterable, Sequence
from pathlib import Path

import pytest

from field_quality_agents.data.schema import (
    COMPLAINT_COLUMNS,
    INVESTIGATION_COLUMNS,
    RECALL_COLUMNS,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LONG_NARRATIVE = (
    "Synthetic complaint narrative long enough for the eighty character floor. "
    "It describes an intermittent electrical fault reported to a dealer. "
) * 2


def _row(columns: Sequence[str], values: dict[str, str]) -> list[str]:
    unknown = set(values) - set(columns)
    if unknown:
        raise ValueError(f"unknown columns: {sorted(unknown)}")
    return [values.get(name, "") for name in columns]


def complaint_rows(
    case_id: str,
    received: str,
    *,
    make: str = "HONDA",
    model: str = "ACCORD",
    year: str = "2021",
    components: Sequence[str] = ("ELECTRICAL SYSTEM:WIRING",),
    narrative: str = LONG_NARRATIVE,
    crash: str = "N",
    fire: str = "N",
    injured: str = "0",
    deaths: str = "0",
    mileage: str = "42000",
) -> list[list[str]]:
    rows: list[list[str]] = []
    for component in components:
        rows.append(
            _row(
                COMPLAINT_COLUMNS,
                {
                    "CMPLID": case_id,
                    "MFR_NAME": "Synthetic Motors",
                    "MAKETXT": make,
                    "MODELTXT": model,
                    "YEARTXT": year,
                    "CRASH": crash,
                    "FIRE": fire,
                    "INJURED": injured,
                    "DEATHS": deaths,
                    "COMPDESC": component,
                    "CITY": "Synthetic City",
                    "STATE": "ZZ",
                    "VIN": "SYNTHETICVIN",
                    "DATEA": received,
                    "LDATE": received,
                    "MILES": mileage,
                    "CDESCR": narrative,
                    "CMPL_TYPE": "IVOQ",
                    "DEALER_NAME": "Synthetic Dealer",
                    "DEALER_TEL": "555-0100",
                    "VEHICLE_OPERATOR": "Synthetic Operator",
                },
            )
        )
    return rows


def recall_rows(
    campaign: str,
    received: str,
    *,
    make: str = "HONDA",
    model: str = "ACCORD",
    year: str = "2021",
    component: str = "ELECTRICAL SYSTEM:WIRING",
    summary: str = "Synthetic recall summary.",
) -> list[list[str]]:
    return [
        _row(
            RECALL_COLUMNS,
            {
                "RECORD_ID": "1",
                "CAMPNO": campaign,
                "MAKETXT": make,
                "MODELTXT": model,
                "YEARTXT": year,
                "COMPNAME": component,
                "RCDATE": received,
                "DATEA": received,
                "ODATE": received,
                "DESC_DEFECT": summary,
            },
        )
    ]


def investigation_rows(
    action: str,
    opened: str,
    *,
    make: str = "HONDA",
    model: str = "ACCORD",
    year: str = "2022",
    component: str = "FORWARD COLLISION AVOIDANCE: AUTOMATIC EMERGENCY BRAKING",
    summary: str = "Synthetic investigation summary.",
) -> list[list[str]]:
    return [
        _row(
            INVESTIGATION_COLUMNS,
            {
                "NHTSA_ACTION_NUMBER": action,
                "MAKE": make,
                "MODEL": model,
                "YEAR": year,
                "COMPNAME": component,
                "MFR_NAME": "Synthetic Motors",
                "ODATE": opened,
                "CDATE": "",
                "CAMPNO": "",
                "SUBJECT": "Synthetic subject",
                "SUMMARY": summary,
            },
        )
    ]


def _write_tsv(path: Path, rows: Iterable[Sequence[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write("\t".join(row) + "\n")


def write_fixture_raw(root: Path) -> Path:
    """Write one small raw snapshot and return the raw directory."""
    raw = root / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    older: list[list[str]] = []
    newer: list[list[str]] = []
    for row in [
        *complaint_rows("C1", "20210101"),
        *complaint_rows("C2", "20220201", year="2022", components=["ELECTRICAL SYSTEM:ADAS"]),
        *complaint_rows(
            "C3",
            "20220301",
            components=["ELECTRICAL SYSTEM:WIRING", "ENGINE"],
        ),
        *complaint_rows(
            "C4",
            "20220401",
            components=["ELECTRICAL SYSTEM:WIRING", "EXTERIOR LIGHTING"],
        ),
        *complaint_rows("C5", "20220501", narrative="Too short."),
        *complaint_rows(
            "C6",
            "20220601",
            narrative=LONG_NARRATIVE + " Reach me at synthetic@example.com.",
        ),
        *complaint_rows("C10", "20220701", year=""),
    ]:
        older.append(row)
    for row in [
        *complaint_rows("C7", "20250601", crash="Y", components=["AIR BAGS"]),
        *complaint_rows("C8", "20250602", components=["EXTERIOR LIGHTING"]),
        *complaint_rows("C9", "20261001", components=["ELECTRICAL SYSTEM:WIRING"]),
        *complaint_rows("C11", "20261030", components=["ELECTRICAL SYSTEM:WIRING"]),
    ]:
        newer.append(row)

    _write_tsv(raw / "COMPLAINTS_RECEIVED_2020-2024.txt", older)
    _write_tsv(raw / "COMPLAINTS_RECEIVED_2025-2026.txt", newer)
    _write_tsv(
        raw / "FLAT_RCL_POST_2010.txt",
        [
            *recall_rows("R1", "20210301"),
            *recall_rows("R2", "20210401", component="ENGINE"),
        ],
    )
    _write_tsv(
        raw / "FLAT_INV.txt",
        [*investigation_rows("I1", "20220301", year="2022")],
    )
    return raw


def copy_groups(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO_ROOT / "data" / "groups.toml", out_dir / "groups.toml")


@pytest.fixture(scope="module")
def fixture_raw(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return write_fixture_raw(tmp_path_factory.mktemp("raw"))
