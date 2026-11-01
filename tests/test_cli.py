from __future__ import annotations

from pathlib import Path

import pytest

from field_quality_agents.cli import build_parser, main

COMMANDS = ["data", "baseline", "issues", "report", "serve", "export", "mcp"]


@pytest.mark.parametrize("command", COMMANDS)
def test_every_command_parses(command: str) -> None:
    args = build_parser().parse_args([command])
    assert args.command == command


def test_run_accepts_replay_and_record() -> None:
    parser = build_parser()
    assert parser.parse_args(["run", "--mode", "replay"]).mode == "replay"
    assert parser.parse_args(["run", "--mode", "record"]).mode == "record"


def test_run_rejects_live_mode() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["run", "--mode", "live"])


def test_issues_and_report_explain_a_missing_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["issues", "--results-dir", str(tmp_path)]) == 1
    assert main(["report", "--results-dir", str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert "no recorded run" in captured.err
    assert captured.out == ""


def test_run_parser_accepts_fixture_inputs() -> None:
    args = build_parser().parse_args(
        [
            "run",
            "--mode",
            "replay",
            "--fixture-sql",
            "fixture.sql",
            "--recordings-dir",
            "recordings",
            "--run-id",
            "demo",
        ]
    )
    assert args.fixture_sql == "fixture.sql"
    assert args.recordings_dir == "recordings"
    assert args.run_id == "demo"


def test_serve_accepts_live_mode() -> None:
    args = build_parser().parse_args(["serve", "--mode", "live", "--live-limit", "3"])
    assert args.mode == "live"
    assert args.live_limit == 3


def test_baseline_parser_accepts_paths() -> None:
    args = build_parser().parse_args(
        ["baseline", "--data-dir", "d", "--out-dir", "o", "--keywords", "k.toml"]
    )
    assert args.data_dir == "d"
    assert args.out_dir == "o"
    assert args.keywords == "k.toml"


def test_data_parser_accepts_refresh_and_skip_fetch() -> None:
    parser = build_parser()
    assert parser.parse_args(["data", "--refresh"]).refresh is True
    assert parser.parse_args(["data", "--skip-fetch"]).skip_fetch is True
    assert parser.parse_args(["data", "--raw-dir", "raw"]).raw_dir == "raw"
