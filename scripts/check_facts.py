#!/usr/bin/env python3
"""Cross-check ``project-facts.yml`` against the committed results.

Every number in ``README.md`` is declared in ``project-facts.yml`` together with
the committed file under ``results/`` it comes from. This script re-derives each
one and fails when the source disagrees, when a source is not tracked by git,
or when the README no longer contains the number. It also checks the document
set, the version string and the screenshot inventory.

Run with ``make facts``.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from itertools import product
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "project-facts.yml"
README = ROOT / "README.md"
CHANGELOG = ROOT / "CHANGELOG.md"
PYPROJECT = ROOT / "pyproject.toml"
PACKAGE_INIT = ROOT / "src" / "field_quality_agents" / "__init__.py"
VERSION_LINE = re.compile(r'^__version__ = "(?P<version>[^"]+)"$', re.MULTILINE)
TOLERANCE = 1e-9


class FactsError(Exception):
    """One fact cannot be verified as declared."""


def _read_json(relative: str) -> Any:
    path = ROOT / relative
    if not path.is_file():
        raise FactsError(f"missing file {relative}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FactsError(f"{relative} is not valid JSON: {exc}") from exc


def _resolve(data: Any, dotted: str) -> Any:
    """Walk ``a.b.0.c`` through objects and list indices."""

    current = data
    for part in dotted.split("."):
        if isinstance(current, list):
            try:
                index = int(part)
            except ValueError as exc:
                raise FactsError(f"path {dotted!r}: {part!r} is not a list index") from exc
            if not 0 <= index < len(current):
                raise FactsError(f"path {dotted!r}: index {index} is out of range")
            current = current[index]
        elif isinstance(current, dict):
            if part not in current:
                raise FactsError(f"path {dotted!r} has no {part!r}")
            current = current[part]
        else:
            raise FactsError(f"path {dotted!r} walks into a {type(current).__name__}")
    return current


def _source_value(source: str) -> tuple[Any, str]:
    """Return ``(value, file)`` for ``results/file.json#dotted.path``."""

    relative, _, dotted = source.partition("#")
    if not relative.startswith("results/"):
        raise FactsError(f"source {relative!r} is not under results/")
    data = _read_json(relative)
    return (_resolve(data, dotted) if dotted else data), relative


def _elements(data: Any) -> list[Any]:
    """Flatten a list, an object of objects, or an object of lists."""

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        values = list(data.values())
        if values and all(isinstance(value, list) for value in values):
            return [item for value in values for item in value]
        return values
    raise FactsError("expected a list or an object of objects")


def _evaluate(spec: dict[str, Any]) -> Any:
    kind = spec.get("kind")
    relative = spec.get("file")
    if not isinstance(relative, str):
        raise FactsError("a check needs a file")
    if kind == "json":
        return _resolve(_read_json(relative), str(spec["path"]))
    if kind == "length":
        data = _read_json(relative)
        if not isinstance(data, (list, dict)):
            raise FactsError(f"{relative} has no length")
        return len(data)
    if kind == "sum_lengths":
        data = _read_json(relative)
        if isinstance(data, dict):
            return sum(len(value) for value in data.values())
        if isinstance(data, list):
            return sum(len(value) for value in data)
        raise FactsError(f"{relative} is not a collection of collections")
    if kind == "count_field":
        field = str(spec["field"])
        expected = spec.get("equals", True)
        return sum(1 for item in _elements(_read_json(relative)) if item.get(field) == expected)
    if kind == "count_collections":
        data = _read_json(relative)
        if not isinstance(data, dict):
            raise FactsError(f"{relative} is not an object of collections")
        field = str(spec["field"])
        expected = spec.get("equals", True)
        return sum(
            1
            for items in data.values()
            if isinstance(items, list) and any(item.get(field) == expected for item in items)
        )
    if kind == "weekly_reports":
        data = _read_json(relative)
        if not isinstance(data, list):
            raise FactsError(f"{relative} is not a list of weekly reports")
        latest = (ROOT / relative).parent / "report.json"
        return len(data) + (1 if latest.is_file() else 0)
    raise FactsError(f"unknown check kind {kind!r}")


def _tracked_files() -> set[str] | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return {item.decode("utf-8") for item in completed.stdout.split(b"\0") if item}


class Checker:
    """Collect failures instead of stopping at the first one."""

    def __init__(self, facts: dict[str, Any], readme: str, tracked: set[str] | None) -> None:
        self.facts = facts
        self.readme = readme
        self.lines = readme.splitlines()
        self.tracked = tracked
        self.errors: list[str] = []
        self.notes: list[str] = []
        self.headline_count = 0
        self.fact_count = 0

    def fail(self, message: str) -> None:
        self.errors.append(message)

    def _tracked(self, relative: str, what: str) -> None:
        if self.tracked is not None and relative not in self.tracked:
            self.fail(f"{what}: {relative} is not tracked by git")

    def check_project(self) -> None:
        project = self.facts.get("project")
        if not isinstance(project, dict):
            self.fail("project-facts.yml has no project block")
            return
        for key in ("name", "tagline", "question", "licence", "version", "model"):
            if not str(project.get(key, "")).strip():
                self.fail(f"project.{key} is empty")
        licence = str(project.get("licence", ""))
        licence_text = ROOT / "LICENSE"
        if not licence_text.is_file() or licence not in licence_text.read_text(encoding="utf-8"):
            self.fail(f"LICENSE does not state the {licence!r} licence")
        version = str(project.get("version", ""))
        try:
            declared = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
        except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
            self.fail(f"pyproject.toml: cannot read the version ({exc})")
        else:
            if declared != version:
                self.fail(f"pyproject.toml says version {declared!r}, facts say {version!r}")
        match = VERSION_LINE.search(PACKAGE_INIT.read_text(encoding="utf-8"))
        if match is None:
            self.fail("src/field_quality_agents/__init__.py has no __version__")
        elif match.group("version") != version:
            self.fail(f"package version {match.group('version')!r} differs from facts {version!r}")
        if not CHANGELOG.is_file():
            self.fail("CHANGELOG.md is missing")
        elif f"[{version}]" not in CHANGELOG.read_text(encoding="utf-8"):
            self.fail(f"CHANGELOG.md has no [{version}] section")

    def check_run(self) -> None:
        run = self.facts.get("run")
        if not isinstance(run, dict):
            self.fail("project-facts.yml has no run block")
            return
        for key in (
            "id",
            "replay_id",
            "set",
            "mode",
            "model",
            "prompt_version",
            "recording_digest",
            "source",
            "replay_source",
        ):
            if not str(run.get(key, "")).strip():
                self.fail(f"run.{key} is empty")
        for key, manifest_file in (("source", "record"), ("replay_source", "replay")):
            source = str(run.get(key, ""))
            if not source.startswith("results/"):
                self.fail(f"run.{key} {source!r} is not under results/")
                continue
            self._tracked(source, f"run.{key}")
            try:
                manifest = _read_json(source)
            except FactsError as exc:
                self.fail(f"run.{key}: {exc}")
                continue
            expected = {
                "set": manifest.get("set_name"),
                "model": manifest.get("model"),
                "prompt_version": manifest.get("prompt_version"),
                "recording_digest": manifest.get("record_digest"),
            }
            if manifest_file == "record":
                expected.update({"id": manifest.get("run_id"), "mode": manifest.get("mode")})
            else:
                expected.update({"replay_id": manifest.get("run_id")})
            for field, actual in expected.items():
                declared = str(run.get(field, ""))
                if declared != str(actual):
                    self.fail(f"run.{field} is {declared!r}, {source} says {actual!r}")
        # The replayed run is the same run from the same recordings, so the
        # reproducible manifest must agree with the record-mode one. Step counts
        # are recomputed by the current pipeline (Q13 added quote verification
        # steps), so they are compared by the facts below, not here.
        try:
            record = _read_json(str(run.get("source")))
            replay = _read_json(str(run.get("replay_source")))
        except FactsError:
            return
        for field in ("case_count", "spend_usd", "record_digest", "set_name", "model"):
            if record.get(field) != replay.get(field):
                self.fail(
                    f"record and replay manifests disagree on {field}: "
                    f"{record.get(field)!r} vs {replay.get(field)!r}"
                )

    def check_headlines(self) -> None:
        entries = self.facts.get("headline")
        if not isinstance(entries, list) or not entries:
            self.fail("project-facts.yml has no headline list")
            return
        seen: set[str] = set()
        for entry in entries:
            identifier = str(entry.get("id", "?"))
            if identifier in seen:
                self.fail(f"headline id {identifier!r} is duplicated")
            seen.add(identifier)
            self.headline_count += 1
            label = str(entry.get("label", ""))
            digits = entry.get("display")
            if not label or not isinstance(digits, int):
                self.fail(f"headline {identifier}: needs a label and integer display")
                continue
            row = next((line for line in self.lines if label in line), None)
            if row is None:
                self.fail(f"README has no row for headline {identifier} ({label!r})")
                continue
            for side in ("before", "after"):
                source = entry.get(f"{side}_source")
                declared = entry.get(side)
                if source is None:
                    if declared is not None:
                        self.fail(f"headline {identifier}: {side} has no source")
                    elif side == "before" and "—" not in row:
                        self.fail(f"headline {identifier}: README row needs an em dash for {side}")
                    continue
                try:
                    actual, relative = _source_value(str(source))
                    self._tracked(relative, f"headline {identifier}")
                except FactsError as exc:
                    self.fail(f"headline {identifier} {side}: {exc}")
                    continue
                if relative not in self.readme:
                    self.fail(f"README does not name the source file {relative}")
                if actual is None or declared is None:
                    self.fail(
                        f"headline {identifier} {side}: source is {actual!r}, "
                        f"facts say {declared!r}"
                    )
                    continue
                scale = float(entry.get("scale", 1.0))
                expected = round(float(actual) * scale, digits)
                if abs(expected - float(declared)) > TOLERANCE:
                    self.fail(
                        f"headline {identifier} {side}: source {relative} gives {expected}, "
                        f"facts say {declared}"
                    )
                    continue
                formatted = f"{float(declared):.{digits}f}"
                if formatted not in row:
                    self.fail(f"headline {identifier}: README row does not contain {formatted!r}")

    def check_facts(self) -> None:
        entries = self.facts.get("facts")
        if not isinstance(entries, list) or not entries:
            self.fail("project-facts.yml has no facts list")
            return
        seen: set[str] = set()
        for entry in entries:
            identifier = str(entry.get("id", "?"))
            if identifier in seen:
                self.fail(f"fact id {identifier!r} is duplicated")
            seen.add(identifier)
            self.fact_count += 1
            spec = entry.get("check")
            if not isinstance(spec, dict):
                self.fail(f"fact {identifier}: needs a check block")
                continue
            relative = str(spec.get("file", ""))
            if not relative.startswith("results/"):
                self.fail(f"fact {identifier}: {relative!r} is not under results/")
                continue
            self._tracked(relative, f"fact {identifier}")
            try:
                actual = _evaluate(spec)
            except FactsError as exc:
                self.fail(f"fact {identifier}: {exc}")
                continue
            declared = entry.get("value")
            if isinstance(declared, str):
                verified = str(actual) == declared
            else:
                try:
                    verified = abs(float(actual) - float(declared)) <= TOLERANCE
                except (TypeError, ValueError):
                    verified = False
            if not verified:
                self.fail(f"fact {identifier}: {relative} gives {actual!r}, facts say {declared!r}")
            display = entry.get("display")
            if display and str(display) not in self.readme:
                self.fail(f"fact {identifier}: README does not contain {display!r}")

    def check_screenshots(self) -> None:
        block = self.facts.get("screenshots")
        if not isinstance(block, dict):
            self.fail("project-facts.yml has no screenshots block")
            return
        directory = ROOT / str(block.get("dir", "results/screenshots"))
        pages = [str(page) for page in block.get("pages", [])]
        widths = [int(width) for width in block.get("widths", [])]
        themes = [str(theme) for theme in block.get("themes", [])]
        expected = [
            f"{page}-{width}-{theme}.png" for page, width, theme in product(pages, widths, themes)
        ]
        for name in block.get("readme", []):
            if str(name) not in self.readme:
                self.fail(f"README does not reference the screenshot {name}")
        if not directory.is_dir():
            self.notes.append(
                f"screenshots: {directory.relative_to(ROOT).as_posix()} is not present yet "
                "(Q10); the inventory is checked when it lands"
            )
            return
        missing = [name for name in expected if not (directory / name).is_file()]
        if missing:
            self.fail(
                f"screenshots: {len(missing)} of {len(expected)} missing, first {missing[0]}"
            )

    def check_documents(self) -> None:
        block = self.facts.get("documents")
        if not isinstance(block, dict):
            self.fail("project-facts.yml has no documents block")
            return
        for document in block.get("required", []):
            path = ROOT / str(document)
            if not path.is_file() or not path.read_text(encoding="utf-8").strip():
                self.fail(f"document {document} is missing or empty")
        for command in block.get("readme_commands", []):
            if str(command) not in self.readme:
                self.fail(f"README does not show the quickstart command {command!r}")
        for heading in block.get("readme_sections", []):
            if str(heading) not in self.lines:
                self.fail(f"README is missing the section {heading!r}")

    def run(self) -> int:
        self.check_project()
        self.check_run()
        self.check_headlines()
        self.check_facts()
        self.check_screenshots()
        self.check_documents()
        for note in self.notes:
            print(f"facts: note {note}")
        if self.tracked is None:
            print("facts: note git is unavailable, so the tracked-file check was skipped")
        if self.errors:
            for message in self.errors:
                print(f"facts: FAIL {message}", file=sys.stderr)
            print(f"facts: {len(self.errors)} problem(s)", file=sys.stderr)
            return 1
        print(
            "facts: ok "
            f"({self.headline_count} headline rows, {self.fact_count} facts, "
            "all traced to committed results/)"
        )
        return 0


def main() -> int:
    if not FACTS.is_file():
        print("facts: FAIL project-facts.yml is missing", file=sys.stderr)
        return 1
    try:
        loaded = yaml.safe_load(FACTS.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"facts: FAIL project-facts.yml is not valid YAML: {exc}", file=sys.stderr)
        return 1
    if not isinstance(loaded, dict):
        print("facts: FAIL project-facts.yml must be a mapping", file=sys.stderr)
        return 1
    if loaded.get("schema") != 1:
        print("facts: FAIL project-facts.yml schema must be 1", file=sys.stderr)
        return 1
    if not README.is_file():
        print("facts: FAIL README.md is missing", file=sys.stderr)
        return 1
    readme = README.read_text(encoding="utf-8")
    return Checker(loaded, readme, _tracked_files()).run()


if __name__ == "__main__":
    sys.exit(main())
