"""Command line entry point.

``fqa run`` is the end-to-end replay/record pipeline. ``fqa issues`` and
``fqa report`` inspect a recorded run; ``fqa export`` writes the dashboard data.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from field_quality_agents import __version__
from field_quality_agents.contracts import RunMode

_RECORDINGS_DIR = Path("recordings")
_FIXTURE_RECORDINGS = Path("tests/fixtures/recordings")
_FIXTURE_SQL = Path("tests/fixtures/e2e/replay_2025.sql")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fqa",
        description="Field quality agents: data, pipelines, dashboard and MCP tools.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    data = sub.add_parser("data", help="fetch and derive the NHTSA data (Q1)")
    data.add_argument(
        "--refresh",
        action="store_true",
        help="re-download every NHTSA source before building",
    )
    data.add_argument(
        "--skip-fetch",
        action="store_true",
        help="build from the existing data/raw files",
    )
    data.add_argument("--raw-dir", default="data/raw", help="raw data directory")
    data.add_argument("--out-dir", default="data", help="derived data directory")
    data.set_defaults(handler="data")

    baseline = sub.add_parser("baseline", help="run the linear baseline (Q3)")
    baseline.add_argument("--data-dir", default="data", help="derived data directory")
    baseline.add_argument("--out-dir", default="results/baseline", help="results directory")
    baseline.add_argument(
        "--keywords",
        default=None,
        help="keyword TOML path (default: config/keywords.toml)",
    )
    baseline.set_defaults(handler="baseline")

    run = sub.add_parser("run", help="play a case set through the desk (Q8)")
    run.add_argument(
        "--mode",
        required=True,
        choices=("replay", "record"),
        help="replay a recorded run, or record live model calls",
    )
    run.add_argument("--set", dest="set_name", default="replay_2025")
    run.add_argument("--run-id", default=None)
    run.add_argument(
        "--recordings-dir",
        default=None,
        help="recordings root (default: recordings/ when it has turns, else the fixtures)",
    )
    run.add_argument(
        "--data-dir",
        default=None,
        help="derived parquet directory (default: data)",
    )
    run.add_argument(
        "--db",
        default=None,
        help="fixture DuckDB to read instead of the committed parquet",
    )
    run.add_argument(
        "--fixture-sql",
        default=None,
        help="build a temporary fixture DuckDB from this SQL file",
    )
    run.add_argument("--results-dir", default="results/runs")
    run.add_argument("--baseline-dir", default="results/baseline")
    run.add_argument(
        "--limit",
        type=int,
        default=None,
        help="run only the first N cases in received-date order (Q9 smoke run)",
    )
    run.set_defaults(handler="run")

    issues = sub.add_parser("issues", help="inspect the issues a run opened (Q8)")
    issues.add_argument("--run-id", default=None)
    issues.add_argument("--results-dir", default="results/runs")
    issues.set_defaults(handler="issues")

    report = sub.add_parser("report", help="inspect the weekly reports a run wrote (Q8)")
    report.add_argument("--run-id", default=None)
    report.add_argument("--results-dir", default="results/runs")
    report.set_defaults(handler="report")

    serve = sub.add_parser("serve", help="serve the API and dashboard (Q7/Q8)")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument(
        "--mode",
        default="replay",
        choices=("replay", "live"),
        help="replay a recorded run, or start live decision threads",
    )
    serve.add_argument(
        "--results-dir",
        default="results/runs",
        help="directory holding recorded runs (default: results/runs)",
    )
    serve.add_argument(
        "--run-id",
        default=None,
        help="serve one recorded run instead of the newest",
    )
    serve.add_argument(
        "--recordings-dir",
        default="recordings",
        help="recordings root for live mode (default: recordings)",
    )
    serve.add_argument(
        "--live-limit",
        type=int,
        default=25,
        help="how many live case threads to start (default: 25)",
    )
    serve.add_argument(
        "--static-dir",
        default="web/dist",
        help="built dashboard to serve (default: web/dist)",
    )
    serve.set_defaults(handler="serve")

    export = sub.add_parser("export", help="write the offline dashboard data (Q8/Q10)")
    export.add_argument("--out", default="dist/field-quality-agents")
    export.add_argument("--run-id", default=None)
    export.add_argument("--results-dir", default="results/runs")
    export.add_argument(
        "--web-dir",
        default="web/dist",
        help="built dashboard to bundle (default: web/dist; run make web-build first)",
    )
    export.set_defaults(handler="export")

    mcp = sub.add_parser("mcp", help="serve the tool functions over MCP stdio (Q2)")
    mcp.add_argument(
        "--data-dir",
        default=None,
        help="directory with the committed parquet files (default: data)",
    )
    mcp.add_argument(
        "--db",
        default=None,
        help="fixture DuckDB file to read instead of the committed parquet",
    )
    mcp.add_argument(
        "--rulebook",
        default=None,
        help="rulebook TOML path (default: config/rulebook.toml)",
    )
    mcp.set_defaults(handler="mcp")

    return parser


def _run_data(args: argparse.Namespace) -> int:
    from field_quality_agents.data.build import build_all
    from field_quality_agents.data.fetch import fetch_nhtsa

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.out_dir)
    if not args.skip_fetch:
        files = fetch_nhtsa(raw_dir, force=bool(args.refresh))
        print(f"data: {len(files)} source file(s) recorded in {out_dir / 'SNAPSHOT.json'}")
    result = build_all(raw_dir=raw_dir, out_dir=out_dir)
    complaints = result.stats.get("complaints", {})
    if isinstance(complaints, dict):
        print(
            "data: {eligible} eligible complaint(s) from {distinct} distinct".format(
                eligible=complaints.get("eligible_complaints", 0),
                distinct=complaints.get("distinct_complaints", 0),
            )
        )
    for path in result.outputs:
        print(f"data: wrote {path}")
    return 0


def _run_baseline(args: argparse.Namespace) -> int:
    from field_quality_agents.baseline.runner import run_baseline

    report = run_baseline(
        data_dir=args.data_dir,
        out_dir=args.out_dir,
        keywords_path=args.keywords,
    )
    print(f"baseline: {report.cases} case(s) from the replay set")
    print(
        "baseline: keyword macro-F1 "
        f"{report.macro_f1.value:.4f} "
        f"[{report.macro_f1.ci_low:.4f}, {report.macro_f1.ci_high:.4f}], "
        f"coverage {report.coverage.value:.4f}"
    )
    print(
        "baseline: safety precision "
        f"{report.safety_precision.value:.4f}, recall {report.safety_recall.value:.4f}"
    )
    print(
        f"baseline: priority {report.priority}, standard test {report.standard_test}, "
        f"closed no trouble found {report.no_trouble_found}"
    )
    print(f"baseline: TF-IDF reference macro-F1 {report.tfidf_macro_f1.value:.4f}")
    print(f"baseline: wrote {report.out_dir}")
    return 0


def _has_recordings(path: Path) -> bool:
    return path.is_dir() and any(path.rglob("*.json"))


def _resolve_run_inputs(
    args: argparse.Namespace,
) -> tuple[Path, str | None, str | None, str | None]:
    """Return ``(recordings_dir, data_dir, db_path, fixture_sql)``."""

    mode = RunMode(args.mode)
    explicit_source = (
        args.db is not None
        or args.data_dir is not None
        or args.fixture_sql is not None
    )
    if args.recordings_dir is not None:
        recordings = Path(args.recordings_dir)
    elif mode is RunMode.RECORD or _has_recordings(_RECORDINGS_DIR):
        recordings = _RECORDINGS_DIR
    else:
        recordings = _FIXTURE_RECORDINGS

    if args.db is not None:
        return recordings, None, args.db, None
    if args.fixture_sql is not None:
        return recordings, None, None, args.fixture_sql
    if args.data_dir is not None:
        return recordings, args.data_dir, None, None
    if (mode is RunMode.RECORD or recordings != _FIXTURE_RECORDINGS) and not explicit_source:
        return recordings, "data", None, None
    return recordings, None, None, str(_FIXTURE_SQL)


def _run_pipeline(args: argparse.Namespace) -> int:
    from field_quality_agents.llm.errors import PolicyStopError
    from field_quality_agents.run.data import open_source
    from field_quality_agents.run.pipeline import DEFAULT_RUN_ID, execute_run

    recordings, data_dir, db_path, fixture_sql = _resolve_run_inputs(args)
    run_id = args.run_id or DEFAULT_RUN_ID
    mode = RunMode(args.mode)
    try:
        with open_source(
            data_dir=data_dir,
            db_path=db_path,
            fixture_sql=fixture_sql,
        ) as source:
            summary = execute_run(
                source=source,
                recordings_dir=recordings,
                results_dir=Path(args.results_dir),
                run_id=run_id,
                set_name=args.set_name,
                mode=mode,
                baseline_dir=Path(args.baseline_dir),
                limit=args.limit,
            )
    except PolicyStopError as exc:
        # PLAN §10 rule 3: the error has already written reports/STOP.md.
        print(f"run: STOPPED, {exc}", file=sys.stderr)
        print("run: see reports/STOP.md; make no further model calls", file=sys.stderr)
        return 3
    print(
        f"run: {summary.cases} case(s), {summary.issues} issue(s), "
        f"{summary.reports} weekly report(s)"
    )
    print(
        f"run: {summary.steps} step(s), spend USD {summary.spend_usd:.6f}, "
        f"{summary.budget_hits} budget hit(s)"
    )
    print(f"run: recordings {recordings} digest {summary.record_digest}")
    print(f"run: wrote {summary.directory}")
    return 0


def _run_issues(args: argparse.Namespace) -> int:
    from field_quality_agents.api import FileResultStore

    store = FileResultStore(args.results_dir, run_id=args.run_id)
    if store.active_run_id() is None:
        print(f"issues: no recorded run under {args.results_dir}", file=sys.stderr)
        return 1
    issues = list(store.issues())
    print(f"issues: {len(issues)} issue(s) in run {store.active_run_id()}")
    for record in issues:
        issue = record.issue
        print(
            f"issues: {issue.id} {issue.opened_at.isoformat()} "
            f"{issue.make} {issue.model} {issue.year} {issue.group} "
            f"observed={issue.observed} threshold={issue.threshold:g}"
        )
    return 0


def _run_report(args: argparse.Namespace) -> int:
    from field_quality_agents.api import FileResultStore

    store = FileResultStore(args.results_dir, run_id=args.run_id)
    if store.active_run_id() is None:
        print(f"report: no recorded run under {args.results_dir}", file=sys.stderr)
        return 1
    reports = sorted(store.weekly_reports(), key=lambda item: item.week_start)
    if not reports:
        print(f"report: run {store.active_run_id()} has no weekly report", file=sys.stderr)
        return 1
    latest = reports[-1]
    print(
        f"report: {latest.week_start.isoformat()}..{latest.week_end.isoformat()} "
        f"{latest.cases_received} case(s) received, {latest.cases_decided} decided, "
        f"{latest.open_issues} open issue(s)"
    )
    print(latest.narrative)
    return 0


def _run_serve(args: argparse.Namespace) -> int:
    import uvicorn

    if args.mode == "live":
        from field_quality_agents.run.live import build_live_app

        app = build_live_app(
            results_dir=args.results_dir,
            run_id=args.run_id,
            recordings_dir=args.recordings_dir,
            static_dir=args.static_dir,
            live_limit=args.live_limit,
        )
    else:
        from field_quality_agents.api import FileResultStore, create_app

        store = FileResultStore(args.results_dir, run_id=args.run_id)
        app = create_app(store=store, mode="replay", static_dir=args.static_dir)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def _run_export(args: argparse.Namespace) -> int:
    from field_quality_agents.export.site import build_static_export

    root = build_static_export(
        results_dir=args.results_dir,
        run_id=args.run_id,
        out_dir=args.out,
        web_dir=args.web_dir,
    )
    cases = 0
    manifest = root / "data" / "manifest.json"
    if manifest.is_file():
        import json

        cases = int(json.loads(manifest.read_text(encoding="utf-8"))["counts"]["cases"])
    print(f"export: wrote the offline dashboard to {root} ({cases} cases)")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.handler == "data":
        return _run_data(args)
    if args.handler == "baseline":
        return _run_baseline(args)
    if args.handler == "run":
        return _run_pipeline(args)
    if args.handler == "issues":
        return _run_issues(args)
    if args.handler == "report":
        return _run_report(args)
    if args.handler == "serve":
        return _run_serve(args)
    if args.handler == "export":
        return _run_export(args)
    if args.handler == "mcp":
        from field_quality_agents.mcp_server import serve

        return serve(
            data_dir=args.data_dir,
            db_path=args.db,
            rulebook_path=args.rulebook,
        )
    print(f"fqa {args.command}: unknown command.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
