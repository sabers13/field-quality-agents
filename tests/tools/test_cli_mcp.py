from __future__ import annotations

from pytest import MonkeyPatch

from field_quality_agents.cli import main


def test_mcp_command_passes_database_flags(monkeypatch: MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    def fake_serve(**kwargs: object) -> int:
        calls.update(kwargs)
        return 0

    monkeypatch.setattr("field_quality_agents.mcp_server.serve", fake_serve)
    assert main(["mcp", "--db", "fixture.duckdb", "--rulebook", "rules.toml"]) == 0
    assert calls == {"data_dir": None, "db_path": "fixture.duckdb", "rulebook_path": "rules.toml"}
