"""Serving the built dashboard with an SPA fallback."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from field_quality_agents.api import create_app
from field_quality_agents.api.store import MemoryResultStore


def _dist(root: Path) -> Path:
    dist = root / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>dashboard</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    return dist


def test_index_assets_and_spa_fallback(tmp_path: Path) -> None:
    dist = _dist(tmp_path)
    (tmp_path / "secret.txt").write_text("do not serve", encoding="utf-8")
    app = create_app(store=MemoryResultStore(), static_dir=dist)

    with TestClient(app) as client:
        assert client.get("/").text == "<html>dashboard</html>"
        asset = client.get("/assets/app.js")
        assert asset.status_code == 200
        assert "console.log" in asset.text
        assert client.get("/cases/C-2025-0001").text == "<html>dashboard</html>"
        traversal = client.get("/%2e%2e/secret.txt")
        assert "do not serve" not in traversal.text

        api = client.get("/api/nope")
        assert api.status_code == 404
        assert api.json()["detail"] == "not found"


def test_missing_build_returns_a_clear_404(tmp_path: Path) -> None:
    app = create_app(store=MemoryResultStore(), static_dir=tmp_path / "missing")

    with TestClient(app) as client:
        root = client.get("/")
        assert root.status_code == 404
        assert "make web-build" in root.json()["detail"]
        assert client.get("/cases/C-1").status_code == 404
