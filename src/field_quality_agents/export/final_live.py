"""Read Q14's final live run for the dashboard panel.

The panel needs two committed files and nothing else:

* ``results/final-live/metrics.json`` — the before/after pair on the 150 unseen
  cases, with the linear baseline read from ``results/final-live/baseline/``;
* the Q9 run's ``metrics.json`` (``results/runs/replay/metrics.json`` by
  default) — the 600-case numbers the final live test is compared with.

No model runs here and no number is invented: a missing file means the panel is
absent. ``make all`` regenerates the offline export from these committed files,
so the export stays byte-identical.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from pydantic import TypeAdapter, ValidationError

from field_quality_agents.api.models import FinalLiveData, FinalLiveSide
from field_quality_agents.contracts import Metrics, RunManifest

__all__ = ["DEFAULT_FINAL_LIVE_DIR", "DEFAULT_Q9_METRICS", "load_final_live"]

DEFAULT_FINAL_LIVE_DIR = Path("results/final-live")
DEFAULT_Q9_METRICS = Path("results/runs/replay/metrics.json")

_METRICS = TypeAdapter(Metrics)
_MANIFEST = TypeAdapter(RunManifest)


def _read_json(path: Path) -> object | None:
    if not path.is_file():
        return None
    try:
        data: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data


def _pair(path: Path) -> FinalLiveSide | None:
    raw = _read_json(path)
    if not isinstance(raw, dict):
        return None
    values = cast(dict[str, object], raw)
    before = values.get("before")
    after = values.get("after")
    if before is None or after is None:
        return None
    try:
        after_metrics = _METRICS.validate_python(after)
        before_metrics = _METRICS.validate_python(before)
    except ValidationError:
        return None
    return FinalLiveSide(
        cases=after_metrics.cases,
        before=before_metrics,
        after=after_metrics,
    )


def load_final_live(
    *,
    final_dir: str | Path = DEFAULT_FINAL_LIVE_DIR,
    q9_metrics: str | Path = DEFAULT_Q9_METRICS,
) -> FinalLiveData | None:
    """Return the panel data, or ``None`` when Q14 has not run yet."""

    directory = Path(final_dir)
    manifest_raw = _read_json(directory / "manifest.json")
    if manifest_raw is None:
        return None
    try:
        manifest = _MANIFEST.validate_python(manifest_raw)
    except ValidationError:
        return None
    final = _pair(directory / "metrics.json")
    q9_path = Path(q9_metrics)
    q9 = _pair(q9_path)
    if final is None or q9 is None:
        return None
    return FinalLiveData(
        run_id=manifest.run_id,
        set_name=manifest.set_name,
        window_start=manifest.started_at.date(),
        window_end=(manifest.completed_at or manifest.started_at).date(),
        spend_usd=manifest.spend_usd,
        steps=manifest.steps,
        budget_hits=manifest.budget_hits,
        final=final,
        q9=q9,
        q9_run_id=q9_path.parent.name,
    )
