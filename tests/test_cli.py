from __future__ import annotations

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


def test_stub_exits_nonzero_with_lane(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["baseline"]) == 2
    captured = capsys.readouterr()
    assert "Q3" in captured.err
    assert captured.out == ""


def test_data_parser_accepts_refresh_and_skip_fetch() -> None:
    parser = build_parser()
    assert parser.parse_args(["data", "--refresh"]).refresh is True
    assert parser.parse_args(["data", "--skip-fetch"]).skip_fetch is True
    assert parser.parse_args(["data", "--raw-dir", "raw"]).raw_dir == "raw"
