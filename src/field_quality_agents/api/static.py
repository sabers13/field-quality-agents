"""Serve ``web/dist`` with an SPA fallback for client-side routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

__all__ = ["add_static_routes"]


def add_static_routes(app: FastAPI, directory: Path) -> None:
    root = directory.resolve()

    def inside(path: str) -> Path | None:
        candidate = (root / path).resolve()
        if candidate != root and root in candidate.parents and candidate.is_file():
            return candidate
        return None

    @app.get("/", include_in_schema=False)
    def dashboard_index() -> FileResponse:
        index = root / "index.html"
        if not index.is_file():
            raise HTTPException(
                status_code=404,
                detail="dashboard build not found; run make web-build first",
            )
        return FileResponse(index)

    @app.get("/{path:path}", include_in_schema=False)
    def dashboard_file(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="not found")
        asset = inside(path)
        if asset is not None:
            return FileResponse(asset)
        fallback = root / "index.html"
        if fallback.is_file():
            return FileResponse(fallback)
        raise HTTPException(
            status_code=404,
            detail="dashboard build not found; run make web-build first",
        )
