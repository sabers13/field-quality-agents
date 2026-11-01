"""The recording digest names only the store a run replays."""

from __future__ import annotations

from pathlib import Path

from field_quality_agents.run.pipeline import recordings_digest


def _turn(directory: Path, name: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.json").write_text("{}", encoding="utf-8")


def test_a_nested_run_store_does_not_change_the_digest(tmp_path: Path) -> None:
    root = tmp_path / "recordings"
    _turn(root / "ab", "key")
    before = recordings_digest(root)

    # Q14 keeps recordings/final-live/ beside Q9's shards. The Q9 digest must
    # not move when another run records into the same parent directory.
    _turn(root / "final-live" / "cd", "other")
    assert recordings_digest(root) == before


def test_a_sharded_turn_changes_the_digest(tmp_path: Path) -> None:
    root = tmp_path / "recordings"
    _turn(root / "ab", "key")
    before = recordings_digest(root)
    _turn(root / "ab", "second")
    assert recordings_digest(root) != before


def test_a_flat_turn_is_part_of_the_digest(tmp_path: Path) -> None:
    root = tmp_path / "recordings"
    _turn(root, "flat")
    before = recordings_digest(root)
    _turn(root, "another")
    assert recordings_digest(root) != before
