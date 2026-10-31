"""Download and record the public NHTSA ODI flat files.

Raw files stay in ``data/raw/`` and are never committed. ``data/SNAPSHOT.json``
records each download's sha256, size, ``Last-Modified`` header and download
time. The committed parquet files built from this snapshot are the project's
source of truth (PLAN section 5).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import urllib.error
import urllib.request
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

__all__ = ["SOURCES", "DownloadedFile", "fetch_nhtsa"]

BASE = "https://static.nhtsa.gov/odi/ffdd"
USER_AGENT = "field-quality-agents/0.1 (public NHTSA data fetch)"
CHUNK = 1024 * 1024


@dataclass(frozen=True)
class DownloadedFile:
    name: str
    path: Path
    sha256: str
    size_bytes: int
    last_modified: str | None
    downloaded_at: datetime


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    role: str
    required: bool = True
    layout_url: str | None = None
    layout_name: str | None = None
    used_in_build: bool = True


SOURCES: tuple[Source, ...] = (
    Source(
        name="COMPLAINTS_RECEIVED_2020-2024",
        url=f"{BASE}/cmpl/COMPLAINTS_RECEIVED_2020-2024.zip",
        role="complaints",
        layout_url=f"{BASE}/cmpl/CMPL.txt",
        layout_name="CMPL.txt",
    ),
    Source(
        name="COMPLAINTS_RECEIVED_2025-2026",
        url=f"{BASE}/cmpl/COMPLAINTS_RECEIVED_2025-2026.zip",
        role="complaints",
        layout_url=f"{BASE}/cmpl/CMPL.txt",
        layout_name="CMPL.txt",
    ),
    Source(
        name="FLAT_RCL_POST_2010",
        url=f"{BASE}/rcl/FLAT_RCL_POST_2010.zip",
        role="recalls",
        layout_url=f"{BASE}/rcl/RCL.txt",
        layout_name="RCL.txt",
    ),
    Source(
        name="FLAT_INV",
        url=f"{BASE}/inv/FLAT_INV.zip",
        role="investigations",
        layout_url=f"{BASE}/inv/INV.txt",
        layout_name="INV.txt",
    ),
    Source(
        name="TSBS_RECEIVED_2020-2024",
        url=f"{BASE}/tsbs/TSBS_RECEIVED_2020-2024.zip",
        role="manufacturer_communications",
        required=False,
        layout_url=f"{BASE}/tsbs/TSBS.txt",
        layout_name="TSBS.txt",
        used_in_build=False,
    ),
    Source(
        name="TSBS_RECEIVED_2025-2026",
        url=f"{BASE}/tsbs/TSBS_RECEIVED_2025-2026.zip",
        role="manufacturer_communications",
        required=False,
        layout_url=f"{BASE}/tsbs/TSBS.txt",
        layout_name="TSBS.txt",
        used_in_build=False,
    ),
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _download(url: str, destination: Path) -> tuple[str, int, str | None]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(request, timeout=180) as response:
        last_modified = response.headers.get("Last-Modified")
        with temporary.open("wb") as handle:
            while chunk := response.read(CHUNK):
                handle.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    os.replace(temporary, destination)
    return digest.hexdigest(), size, last_modified


def _extract(zip_path: Path, expected: str | None = None) -> Path:
    target = zip_path.with_suffix(".txt")
    with zipfile.ZipFile(zip_path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".txt")]
        if len(members) != 1:
            raise ValueError(f"{zip_path}: expected one .txt member, found {members}")
        member = members[0]
        if expected is not None and Path(member).name != expected:
            raise ValueError(f"{zip_path}: expected member {expected}, found {member}")
        temporary = target.with_name(target.name + ".part")
        with archive.open(member) as source, temporary.open("wb") as out:
            shutil.copyfileobj(source, out, CHUNK)
    os.replace(temporary, target)
    return target


def _existing_record(
    source: Source, destination: Path, previous: dict[str, Any] | None
) -> DownloadedFile:
    sha, size = _sha256(destination)
    downloaded_at = datetime.fromtimestamp(destination.stat().st_mtime, UTC).replace(
        microsecond=0
    )
    last_modified = None
    if previous is not None and previous.get("sha256") == sha:
        raw = previous.get("last_modified")
        if isinstance(raw, str):
            last_modified = raw
    return DownloadedFile(
        name=source.name,
        path=destination,
        sha256=sha,
        size_bytes=size,
        last_modified=last_modified,
        downloaded_at=downloaded_at,
    )


def _load_previous(snapshot_path: Path) -> dict[str, dict[str, Any]]:
    if not snapshot_path.is_file():
        return {}
    try:
        raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    records: dict[str, dict[str, Any]] = {}
    for key in ("sources", "optional_sources", "layouts"):
        for item in raw.get(key, []):
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                records[item["name"]] = item
    return records


def _download_layout(
    url: str,
    name: str,
    layout_dir: Path,
    *,
    force: bool,
    previous: dict[str, Any] | None,
) -> DownloadedFile:
    destination = layout_dir / name
    if destination.is_file() and not force:
        layout = Source(name=name, url=url, role="layout")
        return _existing_record(layout, destination, previous)
    sha, size, last_modified = _download(url, destination)
    return DownloadedFile(
        name=name,
        path=destination,
        sha256=sha,
        size_bytes=size,
        last_modified=last_modified,
        downloaded_at=_utcnow(),
    )


def fetch_nhtsa(dest: Path, *, force: bool = False) -> list[DownloadedFile]:
    """Download the sources into ``dest`` and write ``data/SNAPSHOT.json``.

    With ``force=False`` existing archives are reused and hashed locally; no
    network request is made. ``force=True`` re-downloads every source.
    """
    dest.mkdir(parents=True, exist_ok=True)
    snapshot_path = dest.parent / "SNAPSHOT.json"
    previous = _load_previous(snapshot_path)

    downloaded: list[DownloadedFile] = []
    source_records: list[dict[str, Any]] = []
    layout_records: list[dict[str, Any]] = []
    layouts_done: set[str] = set()
    optional_records: list[dict[str, Any]] = []

    for source in SOURCES:
        archive = dest / f"{source.name}.zip"
        record: dict[str, Any] = {
            "name": source.name,
            "role": source.role,
            "url": source.url,
            "required": source.required,
            "used_in_build": source.used_in_build,
        }
        if source.required:
            try:
                if archive.is_file() and not force:
                    item = _existing_record(source, archive, previous.get(source.name))
                else:
                    sha, size, last_modified = _download(source.url, archive)
                    item = DownloadedFile(
                        name=source.name,
                        path=archive,
                        sha256=sha,
                        size_bytes=size,
                        last_modified=last_modified,
                        downloaded_at=_utcnow(),
                    )
                extracted = _extract(archive, expected=f"{source.name}.txt")
            except (OSError, urllib.error.URLError, ValueError) as exc:
                raise RuntimeError(f"fetch_nhtsa: failed for {source.url}: {exc}") from exc
            record.update(
                {
                    "sha256": item.sha256,
                    "size_bytes": item.size_bytes,
                    "last_modified": item.last_modified,
                    "downloaded_at": _iso(item.downloaded_at),
                    "extracted": extracted.name,
                }
            )
            downloaded.append(item)
            source_records.append(record)
        else:
            try:
                if archive.is_file() and not force:
                    item = _existing_record(source, archive, previous.get(source.name))
                else:
                    sha, size, last_modified = _download(source.url, archive)
                    item = DownloadedFile(
                        name=source.name,
                        path=archive,
                        sha256=sha,
                        size_bytes=size,
                        last_modified=last_modified,
                        downloaded_at=_utcnow(),
                    )
                extracted = _extract(archive, expected=f"{source.name}.txt")
            except (OSError, urllib.error.URLError, ValueError) as exc:
                optional_records.append(
                    {
                        "name": source.name,
                        "role": source.role,
                        "url": source.url,
                        "present": False,
                        "note": str(exc),
                    }
                )
                continue
            record.update(
                {
                    "sha256": item.sha256,
                    "size_bytes": item.size_bytes,
                    "last_modified": item.last_modified,
                    "downloaded_at": _iso(item.downloaded_at),
                    "extracted": extracted.name,
                    "present": True,
                }
            )
            optional_records.append(record)
            downloaded.append(item)

        if source.layout_url and source.layout_name:
            if source.layout_name in layouts_done:
                continue
            layout = _download_layout(
                source.layout_url,
                source.layout_name,
                dest / "layout",
                force=force,
                previous=previous.get(source.layout_name),
            )
            layouts_done.add(source.layout_name)
            layout_records.append(
                {
                    "name": layout.name,
                    "url": source.layout_url,
                    "sha256": layout.sha256,
                    "size_bytes": layout.size_bytes,
                    "last_modified": layout.last_modified,
                    "downloaded_at": _iso(layout.downloaded_at),
                }
            )

    snapshot = {
        "dataset": "NHTSA ODI public flat files",
        "snapshot_at": _iso(_utcnow()),
        "sources": source_records,
        "layouts": layout_records,
        "optional_sources": optional_records,
    }
    temporary = snapshot_path.with_name(snapshot_path.name + ".tmp")
    temporary.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, snapshot_path)
    return downloaded


def main(argv: Sequence[str] | None = None) -> int:
    """Small command wrapper used by ``scripts/fetch_nhtsa.py``."""
    import argparse

    parser = argparse.ArgumentParser(description="Download the NHTSA flat files.")
    parser.add_argument("--dest", default="data/raw", help="raw data directory")
    parser.add_argument("--force", action="store_true", help="re-download everything")
    args = parser.parse_args(argv)
    files = fetch_nhtsa(Path(args.dest), force=args.force)
    for item in files:
        print(f"{item.name}: {item.size_bytes} bytes sha256:{item.sha256[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
