"""Serve the built demo UI only under an explicit, local fixture-mode opt-in."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def mount_demo_ui(application: FastAPI, *, fixture_mode: bool, directory: Path) -> None:
    if not fixture_mode:
        raise ValueError("The unauthenticated demo UI requires fixture mode")
    if not (directory / "index.html").is_file():
        raise ValueError("Build the frontend first with npm run build")
    # Mounted last so API routes retain priority. StaticFiles rejects path traversal.
    application.mount("/", StaticFiles(directory=directory, html=True), name="demo-ui")
