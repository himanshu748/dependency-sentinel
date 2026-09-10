import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.http_contract import MAX_REQUEST_BYTES, install_http_contract, runtime_metadata


@pytest.mark.parametrize(
    "status, phrase",
    [
        (401, "access was denied"),
        (403, "access was denied"),
        (429, "usage or capacity"),
        (503, "intentionally stopped"),
    ],
)
def test_provider_failure_is_actionable_without_exposing_credentials(status, phrase):
    class ProviderFailure(Exception):
        status_code = status

    app = client_app()

    @app.get("/api/provider-failure")
    def failure():
        raise ProviderFailure("private-key-and-provider-response")

    response = TestClient(app).get("/api/provider-failure")
    assert response.status_code == 503
    assert phrase in response.json()["detail"]
    assert "private-key" not in response.text


class Payload(BaseModel):
    count: int


def client_app() -> FastAPI:
    app = FastAPI()
    install_http_contract(app)

    @app.get("/api/health")
    def health():
        return runtime_metadata(fixture_mode=True, runtime_arn=None)

    @app.post("/api/input")
    def accept(payload: Payload):
        return {"count": payload.count}

    @app.get("/api/failure")
    def fail():
        raise RuntimeError("private-provider-credential")

    return app


def test_request_id_and_private_response_headers():
    client = TestClient(client_app())
    first = client.get("/api/health", headers={"X-Request-ID": "untrusted-id"})
    second = client.get("/api/health")
    assert first.status_code == 200
    assert len(first.headers["x-request-id"]) == 32
    assert first.headers["x-request-id"] != second.headers["x-request-id"]
    assert first.headers["cache-control"] == "no-store"
    assert first.headers["x-content-type-options"] == "nosniff"
    assert first.headers["referrer-policy"] == "no-referrer"
    assert first.json()["aws_calls_enabled"] is False


def test_remote_browser_origin_is_rejected_without_running_route():
    client = TestClient(client_app())
    response = client.post(
        "/api/input", json={"count": 1}, headers={"Origin": "https://example.org"}
    )
    assert response.status_code == 403
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_only_exact_loopback_hosts_and_origins_are_accepted():
    client = TestClient(client_app())
    for origin in ("http://127.0.0.1:5178", "http://localhost:5180", "http://[::1]:5179"):
        assert client.get("/api/health", headers={"Origin": origin}).status_code == 200
    for origin in ("null", "http://localhost.example.org", "http://127.0.0.2:5178"):
        assert client.get("/api/health", headers={"Origin": origin}).status_code == 403
    for host in ("example.org", "localhost.example.org", "[broken"):
        assert client.get("/api/health", headers={"Host": host}).status_code == 400


def test_request_size_is_bounded_before_json_parsing():
    client = TestClient(client_app())
    response = client.post("/api/input", content="x" * (MAX_REQUEST_BYTES + 1))
    assert response.status_code == 413
    assert response.headers["cache-control"] == "no-store"


def test_streamed_request_size_is_also_bounded():
    client = TestClient(client_app())

    def chunks():
        yield b"x" * MAX_REQUEST_BYTES
        yield b"x"

    assert client.post("/api/input", content=chunks()).status_code == 413


def test_invalid_content_length_is_rejected():
    client = TestClient(client_app())
    for length in ("nope", "-1"):
        response = client.post("/api/input", content="{}", headers={"Content-Length": length})
        assert response.status_code == 400


def test_validation_does_not_echo_rejected_sensitive_values():
    response = TestClient(client_app()).post(
        "/api/input", json={"count": "private-message-contents"}
    )
    assert response.status_code == 422
    assert "private-message-contents" not in response.text
    assert response.json()["detail"][0]["loc"] == ["body", "count"]
    assert "input" not in response.json()["detail"][0]


def test_unhandled_failure_is_safe_and_correlated(caplog):
    response = TestClient(client_app()).get("/api/failure")
    assert response.status_code == 503
    assert "private-provider-credential" not in response.text
    assert "private-provider-credential" not in caplog.text
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert "RuntimeError" in caplog.text


def test_runtime_metadata_never_claims_model_access_was_verified():
    assert runtime_metadata(fixture_mode=False, runtime_arn=None)["runtime_mode"] == "bedrock"
    assert runtime_metadata(fixture_mode=False, runtime_arn="configured") == {
        "runtime_mode": "agentcore",
        "model_access": "not_verified",
        "storage_mode": "local_sqlite",
        "aws_calls_enabled": True,
        "max_request_bytes": MAX_REQUEST_BYTES,
    }
