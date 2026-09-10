"""Serve built assets locally; live use needs an explicit opt-in and HTTP boundaries."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def mount_demo_ui(
    application: FastAPI, *, fixture_mode: bool, directory: Path, local_live_ui: bool = False
) -> None:
    if not fixture_mode and not local_live_ui:
        raise ValueError("The unauthenticated demo UI requires fixture mode")
    if not (directory / "index.html").is_file():
        raise ValueError("Build the frontend first with npm run build")
    # Mounted last so API routes retain priority. StaticFiles rejects path traversal.
    application.mount("/", StaticFiles(directory=directory, html=True), name="demo-ui")
