"""Render ``data/STATS.md`` from the build statistics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

__all__ = ["render_stats"]


def _as_dict(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def _as_int(value: object) -> int:
    return int(value) if isinstance(value, (int, float)) else 0


def _human_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def _pct(part: int, total: int) -> str:
    return f"{100.0 * part / total:.1f}%" if total else "n/a"


def _sources_table(snapshot: Mapping[str, object]) -> list[str]:
    lines = [
        "## Snapshot sources",
        "",
        "| source | role | bytes | sha256 | Last-Modified | downloaded |",
        "|---|---|---:|---|---|---|",
    ]
    sources = snapshot.get("sources")
    if not isinstance(sources, list) or not sources:
        lines.append("| _SNAPSHOT.json missing_ | | | | | |")
    else:
        for entry in sources:
            item = _as_dict(entry)
            sha = str(item.get("sha256", ""))
            lines.append(
                "| {name} | {role} | {size} | `{sha}` | {modified} | {downloaded} |".format(
                    name=item.get("name", ""),
                    role=item.get("role", ""),
                    size=_as_int(item.get("size_bytes")),
                    sha=sha[:12],
                    modified=item.get("last_modified") or "n/a",
                    downloaded=item.get("downloaded_at", ""),
                )
            )
    optional = snapshot.get("optional_sources")
    if isinstance(optional, list) and optional:
        lines.extend(["", "Optional sources:", ""])
        for entry in optional:
            item = _as_dict(entry)
            state = "present" if item.get("present") else "absent"
            lines.append(f"- `{item.get('name', '')}` ({item.get('role', '')}): {state}")
            if item.get("present"):
                lines.append(
                    "  sha256 `{sha}`, {size} bytes".format(
                        sha=str(item.get("sha256", ""))[:12],
                        size=_as_int(item.get("size_bytes")),
                    )
                )
    return lines


def _selection_rows(
    complaints: Mapping[str, object], components: Mapping[str, object]
) -> list[str]:
    rows = [
        ("complaint rows read", _as_int(complaints.get("rows_read"))),
        ("distinct complaints", _as_int(complaints.get("distinct_complaints"))),
        (
            "dropped: more than one product (make/model/year)",
            _as_int(complaints.get("multi_product_dropped")),
        ),
        (
            "complaints whose component rows map to one group",
            _as_int(complaints.get("single_group_complaints")),
        ),
        (
            "dropped: narrative under 80 characters",
            _as_int(complaints.get("narrative_under_80_dropped")),
        ),
        ("dropped: PII screen", _as_int(complaints.get("pii_dropped"))),
        (
            "dropped: missing make, model or year",
            _as_int(complaints.get("missing_product_key_dropped")),
        ),
        ("eligible complaints", _as_int(complaints.get("eligible_complaints"))),
    ]
    lines = ["## Selection", "", "| step | rows |", "|---|---:|"]
    lines.extend(f"| {label} | {value:,} |" for label, value in rows)
    lines.extend(
        [
            "",
            "Component mapping: "
            f"{_as_int(components.get('mapped_component_values')):,} of "
            f"{_as_int(components.get('distinct_component_values')):,} distinct "
            f"component values map to a group "
            f"({_as_int(components.get('unmapped_component_values')):,} unmapped).",
            "",
        ]
    )
    return lines


def _pii_rows(pii: Mapping[str, object]) -> list[str]:
    lines = [
        "## PII screen",
        "",
        "The screen matches a narrative and drops the whole row. Counts overlap",
        "because one narrative can match more than one pattern.",
        "",
        "| pattern | narratives matched |",
        "|---|---:|",
    ]
    for name in ("vin", "email", "phone", "street_address", "any", "screened"):
        lines.append(f"| {name} | {_as_int(pii.get(name)):,} |")
    lines.append("")
    return lines


def _group_rows(
    group_table: Mapping[str, object], descriptions: Mapping[str, object]
) -> list[str]:
    lines = [
        "## Complaints per group",
        "",
        "| group | description | mapped | safety | rate | KB | replay | final | fleet |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for group_id in sorted(group_table):
        item = _as_dict(group_table[group_id])
        total = _as_int(item.get("complaints"))
        safety = _as_int(item.get("safety_relevant"))
        lines.append(
            "| `{gid}` | {desc} | {total:,} | {safety:,} | {rate} | "
            "{kb:,} | {replay:,} | {final:,} | {fleet:,} |".format(
                gid=group_id,
                desc=descriptions.get(group_id, ""),
                total=total,
                safety=safety,
                rate=_pct(safety, total),
                kb=_as_int(item.get("kb")),
                replay=_as_int(item.get("replay")),
                final=_as_int(item.get("final")),
                fleet=_as_int(item.get("fleet_weekly_cases")),
            )
        )
    lines.append("")
    return lines


def _set_rows(sets: Mapping[str, object], final_window: Mapping[str, object]) -> list[str]:
    labels = (
        ("kb", "Knowledge base (2020-2024)"),
        ("replay", "Replay 2025"),
        ("final", "Final live (latest four complete weeks)"),
    )
    lines = ["## Sets", ""]
    for key, label in labels:
        item = _as_dict(sets.get(key))
        rows = _as_int(item.get("rows"))
        safety = _as_int(item.get("safety_relevant"))
        lines.append(
            f"- **{label}:** {rows:,} cases, {safety:,} safety-relevant "
            f"({_pct(safety, rows)})."
        )
    lines.extend(
        [
            "",
            "The final live set is **sealed**: no run, model, prompt or tuning",
            "step may use it before Q14. Its window is "
            f"`{final_window.get('start', 'n/a')}` to "
            f"`{final_window.get('end', 'n/a')}`.",
            "",
        ]
    )
    return lines


def _mapping_rows(
    recalls: Mapping[str, object],
    investigations: Mapping[str, object],
    events: Mapping[str, object],
    summary_chars: int,
) -> list[str]:
    recall_rows = _as_int(recalls.get("rows_read"))
    recall_campaigns = _as_int(recalls.get("campaigns"))
    recall_mapped = _as_int(recalls.get("mapped_rows"))
    recall_mapped_campaigns = _as_int(recalls.get("mapped_campaigns"))
    inv_rows = _as_int(investigations.get("rows_read"))
    inv_actions = _as_int(investigations.get("actions"))
    inv_mapped = _as_int(investigations.get("mapped_rows"))
    inv_mapped_actions = _as_int(investigations.get("mapped_actions"))
    event_rows = _as_int(events.get("rows"))
    event_joined = _as_int(events.get("joined_to_fleet"))
    lines = [
        "## Recalls and investigations",
        "",
        "| source | rows read | distinct ids | rows mapped | ids mapped | rows written |",
        "|---|---:|---:|---:|---:|---:|",
        "| recalls | {rows:,} | {ids:,} | {mapped:,} ({rate}) | "
        "{ids_mapped:,} ({id_rate}) | {written:,} |".format(
            rows=recall_rows,
            ids=recall_campaigns,
            mapped=recall_mapped,
            rate=_pct(recall_mapped, recall_rows),
            ids_mapped=recall_mapped_campaigns,
            id_rate=_pct(recall_mapped_campaigns, recall_campaigns),
            written=_as_int(recalls.get("output_rows")),
        ),
        "| investigations | {rows:,} | {ids:,} | {mapped:,} ({rate}) | "
        "{ids_mapped:,} ({id_rate}) | {written:,} |".format(
            rows=inv_rows,
            ids=inv_actions,
            mapped=inv_mapped,
            rate=_pct(inv_mapped, inv_rows),
            ids_mapped=inv_mapped_actions,
            id_rate=_pct(inv_mapped_actions, inv_actions),
            written=_as_int(investigations.get("output_rows")),
        ),
        "",
        "Event ground truth: {rows:,} rows ({recalls:,} recall, "
        "{investigations:,} investigation); {joined:,} ({rate}) join a fleet "
        "series key.".format(
            rows=event_rows,
            recalls=_as_int(events.get("recalls")),
            investigations=_as_int(events.get("investigations")),
            joined=event_joined,
            rate=_pct(event_joined, event_rows),
        ),
        "",
        f"Recall and investigation summaries are capped at {summary_chars:,}",
        "characters in the committed parquet; the cap keeps the repository under",
        "60 MB while preserving the defect and corrective-action text used for",
        "evidence.",
        "",
    ]
    return lines


def _file_rows(files: Mapping[str, object]) -> list[str]:
    lines = ["## Output files", "", "| file | rows | size |", "|---|---:|---:|"]
    total_bytes = 0
    for name in sorted(files):
        item = _as_dict(files[name])
        size = _as_int(item.get("bytes"))
        total_bytes += size
        lines.append(f"| `{name}` | {_as_int(item.get('rows')):,} | {_human_bytes(size)} |")
    lines.extend(
        [
            f"| **total** | | **{_human_bytes(total_bytes)}** |",
            "",
            "Raw downloads under `data/raw/` and the working DuckDB file are not",
            "committed.",
            "",
        ]
    )
    return lines


def render_stats(stats: Mapping[str, object], snapshot: Mapping[str, object]) -> str:
    complaints = _as_dict(stats.get("complaints"))
    components = _as_dict(stats.get("components"))
    group_table = _as_dict(stats.get("group_table"))
    descriptions = _as_dict(stats.get("group_descriptions"))
    lines: list[str] = [
        "# NHTSA data statistics",
        "",
        "Generated by `fqa data` from the committed snapshot. Do not edit by hand.",
        "",
        f"Snapshot max received date: `{stats.get('snapshot_max_date', 'n/a')}`.",
        "",
        *_sources_table(snapshot),
        "",
        *_selection_rows(complaints, components),
        *_pii_rows(_as_dict(complaints.get("pii_screen"))),
        *_group_rows(group_table, descriptions),
        *_set_rows(_as_dict(stats.get("sets")), _as_dict(stats.get("final_window"))),
        *_mapping_rows(
            _as_dict(stats.get("recalls")),
            _as_dict(stats.get("investigations")),
            _as_dict(stats.get("events")),
            _as_int(stats.get("summary_max_chars")),
        ),
        *_file_rows(_as_dict(stats.get("files"))),
    ]
    return "\n".join(lines)
