from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.web import mount_demo_ui


def test_demo_ui_serves_build_without_shadowing_api(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<h1>Demo build</h1>")
    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    mount_demo_ui(app, fixture_mode=True, directory=tmp_path)
    client = TestClient(app)
    assert "Demo build" in client.get("/").text
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/not-a-route").status_code == 404
    assert client.get("/%2e%2e/private.txt").status_code == 404


def test_demo_ui_refuses_paid_mode(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires fixture mode"):
        mount_demo_ui(FastAPI(), fixture_mode=False, directory=tmp_path)


def test_demo_ui_requires_built_assets(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Build the frontend"):
        mount_demo_ui(FastAPI(), fixture_mode=True, directory=tmp_path)
