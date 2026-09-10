import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_reports_service_without_exposing_configuration_secrets() -> None:
    """Catch a missing route or a response that leaks credential-shaped settings."""
    try:
        from app.main import create_app
    except ImportError:
        pytest.fail("app.main.create_app is not implemented")

    async with AsyncClient(
        transport=ASGITransport(app=create_app()), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload.pop("evidence_mode") == "fixture"
    assert payload.pop("repository_root")
    assert payload == {
        "service": "dependency-sentinel",
        "status": "ok",
        "fixture_mode": True,
        "model_configured": False,
        "runtime_mode": "local",
        "model_access": "disabled",
        "storage_mode": "local_sqlite",
        "aws_calls_enabled": False,
        "max_request_bytes": 262144,
    }
    body = response.text.lower()
    assert "secret" not in body
    assert "access_key" not in body
    assert "token" not in body
