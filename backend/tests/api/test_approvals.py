import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_approval_endpoint_resumes_paused_run(api_app) -> None:
    repository = api_app.state.test_repository
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
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
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "choice,final_status", [("approved", "completed"), ("rejected", "cancelled")]
)
async def test_lost_approval_response_can_be_retried_without_duplicate_events(
    api_app, choice, final_status
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
        created = await client.post(
            "/api/runs",
            json={"repository": str(api_app.state.test_repository)},
            headers={"Idempotency-Key": "retry-decision"},
        )
        run_id = created.json()["run"]["id"]
        body = {"approval_id": "apply-upgrade", "choice": choice}
        first = await client.post(f"/api/runs/{run_id}/approvals", json=body)
        repeated = await client.post(f"/api/runs/{run_id}/approvals", json=body)
        changed = await client.post(
            f"/api/runs/{run_id}/approvals",
            json={**body, "choice": "rejected" if choice == "approved" else "approved"},
        )
    assert first.status_code == repeated.status_code == 200
    assert repeated.json()["status"] == final_status
    assert first.json() == repeated.json()
    assert changed.status_code == 409
    events = api_app.state.store.list_events(run_id)
    assert len(events) == len({event.kind for event in events})
