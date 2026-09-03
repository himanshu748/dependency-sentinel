import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_approval_endpoint_resumes_paused_run(api_app) -> None:
    repository = api_app.state.test_repository
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client:
        created = await client.post(
            "/api/runs",
            json={"repository": str(repository)},
            headers={"Idempotency-Key": "approve-run"},
        )
        run_id = created.json()["run"]["id"]
        approved = await client.post(
            f"/api/runs/{run_id}/approvals",
            json={"approval_id": "apply-upgrade", "choice": "approved"},
        )

    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_approval_endpoint_returns_actionable_gate_error(api_app) -> None:
    repository = api_app.state.test_repository
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client:
        created = await client.post(
            "/api/runs",
            json={"repository": str(repository)},
            headers={"Idempotency-Key": "wrong-gate"},
        )
        rejected = await client.post(
            f"/api/runs/{created.json()['run']['id']}/approvals",
            json={"approval_id": "wrong", "choice": "approved"},
        )

    assert rejected.status_code == 409
    assert rejected.json()["detail"] == {
        "code": "approval_gate_mismatch",
        "message": "approval id does not match the active gate",
    }
