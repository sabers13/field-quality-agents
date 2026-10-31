"""Command line entry point.

Q0 provides the command surface only. Each command reports the lane that will
implement it and exits with status 2, so a half-built pipeline can never look
like a successful run.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from field_quality_agents import __version__

_NOT_IMPLEMENTED = {
    "baseline": "Q3 (linear baseline)",
    "run": "Q8 (end-to-end run)",
    "issues": "Q8 (issue agent)",
    "report": "Q8 (report agent)",
    "serve": "Q7 (FastAPI backend)",
    "export": "Q10 (static export)",
    "mcp": "Q2 (MCP server)",
}


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
    run.set_defaults(handler="run")

    issues = sub.add_parser("issues", help="run the issue agent over a run (Q8)")
    issues.add_argument("--run-id", default=None)
    issues.set_defaults(handler="issues")

    report = sub.add_parser("report", help="generate the weekly report (Q8)")
    report.add_argument("--run-id", default=None)
    report.set_defaults(handler="report")

    serve = sub.add_parser("serve", help="serve the API and dashboard (Q7)")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(handler="serve")

    export = sub.add_parser("export", help="write the offline dashboard export (Q10)")
    export.add_argument("--out", default="dist/field-quality-agents")
    export.set_defaults(handler="export")

    mcp = sub.add_parser("mcp", help="serve the tool functions over MCP stdio (Q2)")
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.handler == "data":
        return _run_data(args)
    lane = _NOT_IMPLEMENTED[args.handler]
    print(
        f"fqa {args.command}: not implemented in the Q0 scaffold; this lands in {lane}.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
