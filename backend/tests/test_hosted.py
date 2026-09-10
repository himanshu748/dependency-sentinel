import sqlite3
from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.hosted import COOKIE, HostedGateway, Registry


def gateway(tmp_path, **kwargs):
    assets = tmp_path / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "index.html").write_text("<h1>Judge workspace</h1>")

    def factory(directory):
        app = FastAPI()
        connection = sqlite3.connect(directory / "test.sqlite3", check_same_thread=False)
        connection.execute("CREATE TABLE IF NOT EXISTS items(value TEXT)")
        app.state.store = SimpleNamespace(_connection=connection)

        @app.get("/api/items")
        def items():
            return [r[0] for r in connection.execute("SELECT value FROM items")]

        @app.post("/api/plans")
        @app.post("/api/runs")
        async def create(request: Request):
            data = await request.json()
            connection.execute("INSERT INTO items VALUES (?)", (data.get("value", "saved"),))
            connection.commit()
            return {"saved": True}

        @app.post("/api/decision")
        def decision():
            return {"approved": True}

        return app

    return HostedGateway(
        origin="https://judge.example",
        root=tmp_path / "data",
        static_directory=assets,
        factory=factory,
        project="test",
        **kwargs,
    )


def client(app):
    result = TestClient(app, base_url="https://judge.example")
    result.headers["Origin"] = "https://judge.example"
    return result


def test_sessions_isolate_records_and_survive_gateway_restart(tmp_path):
    app = gateway(tmp_path)
    first, second = client(app), client(app)
    opened = first.get("/")
    assert "HttpOnly" in opened.headers["set-cookie"]
    assert "Secure" in opened.headers["set-cookie"]
    assert "SameSite=Strict" in opened.headers["set-cookie"]
    second.get("/")
    assert first.post("/api/plans", json={"value": "private"}).status_code == 200
    assert first.get("/api/items").json() == ["private"]
    assert second.get("/api/items").json() == []
    restarted = client(gateway(tmp_path))
    restarted.cookies.update(first.cookies)
    assert restarted.get("/api/items").json() == ["private"]


def test_write_requires_valid_session_and_origin(tmp_path):
    web = client(gateway(tmp_path))
    assert web.post("/api/plans", json={}).status_code == 401
    web.get("/")
    assert (
        web.post("/api/plans", json={}, headers={"Origin": "https://evil.example"}).status_code
        == 403
    )
    del web.headers["Origin"]
    assert web.post("/api/plans", json={}).status_code == 403
    assert web.get("/api/items").json() == []


def test_missing_static_files_return_safe_404(tmp_path):
    web = client(gateway(tmp_path))
    for path in ("/assets/missing.js", "/missing-page"):
        response = web.get(path)
        assert response.status_code == 404
        assert response.json() == {"detail": "Not found."}
        assert response.headers["x-content-type-options"] == "nosniff"


def test_cookie_is_not_a_caller_chosen_database_path(tmp_path):
    web = client(gateway(tmp_path))
    web.cookies.set(COOKIE, "a" * 64)
    web.get("/")
    assert Registry(tmp_path / "data").session("a" * 64) is None


def test_daily_quota_persists_and_does_not_block_approval(tmp_path):
    web = client(gateway(tmp_path, daily_limit=1))
    web.get("/")
    assert web.post("/api/plans", json={}).status_code == 200
    assert web.post("/api/plans", json={}).status_code == 429
    next_web = client(gateway(tmp_path, daily_limit=1))
    next_web.cookies.update(web.cookies)
    assert next_web.post("/api/plans", json={}).status_code == 429
    assert next_web.post("/api/decision", json={}).status_code == 200


def test_host_https_size_and_documentation_boundaries(tmp_path):
    web = client(gateway(tmp_path))
    web.get("/")
    assert web.get("/", headers={"Host": "evil.example"}).status_code == 400
    assert web.get("http://judge.example/").status_code == 400
    assert web.get("/openapi.json").status_code == 404
    assert (
        web.post(
            "/api/plans", content=b"x" * 65537, headers={"Content-Type": "application/json"}
        ).status_code
        == 413
    )
    assert (
        web.post("/api/plans", content="x", headers={"Content-Type": "text/plain"}).status_code
        == 415
    )
    assert web.get("/api/items", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403


def test_public_sentinel_cannot_select_another_repository(tmp_path):
    owned = str(tmp_path / "owned")
    web = client(gateway(tmp_path, owned_repository=owned))
    web.get("/")
    assert web.post("/api/runs", json={"repository": "/etc"}).status_code == 403
    assert (
        web.post("/api/runs", json={"repository": "https://github.com/example/repo"}).status_code
        == 403
    )
    assert web.post("/api/runs", json={"repository": owned}).status_code == 200
    assert web.post("/api/repositories/import", json={}).status_code == 403


def test_quota_reservations_are_atomic(tmp_path):
    registry = Registry(tmp_path)
    assert registry.reserve([("global", 1), ("person-a", 2)])
    assert not registry.reserve([("global", 1), ("person-b", 2)])
    with registry.connect() as db:
        assert db.execute("SELECT count FROM counters WHERE key='person-b'").fetchone() is None


def test_hosting_metadata_has_no_credentials(tmp_path):
    web = client(gateway(tmp_path))
    response = web.get("/api/hosting")
    assert response.status_code == 200
    assert response.json()["provider"] == "Groq"
    assert response.json()["hosted"] is True
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
