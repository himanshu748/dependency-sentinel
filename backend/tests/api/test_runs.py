import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_create_poll_and_idempotently_retry_run(api_app) -> None:
    repository = api_app.state.test_repository
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client:
        first = await client.post(
            "/api/runs",
            json={"repository": str(repository)},
            headers={"Idempotency-Key": "scan-fixture-once"},
        )
        repeated = await client.post(
            "/api/runs",
            json={"repository": str(repository)},
            headers={"Idempotency-Key": "scan-fixture-once"},
        )
        loaded = await client.get(f"/api/runs/{first.json()['run']['id']}")
        events = await client.get(f"/api/runs/{first.json()['run']['id']}/events")

    assert first.status_code == 201
    assert repeated.status_code == 200
    assert repeated.json()["run"]["id"] == first.json()["run"]["id"]
    assert loaded.json()["status"] == "waiting_for_approval"
    assert [event["sequence"] for event in events.json()] == list(range(1, 8))
    assert events.json()[-1]["kind"] == "approval_required"


@pytest.mark.asyncio
async def test_idempotency_key_cannot_be_reused_for_another_repository(api_app, tmp_path) -> None:
    repository = api_app.state.test_repository
    other = tmp_path / "other"
    other.mkdir()
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client:
        await client.post(
            "/api/runs",
            json={"repository": str(repository)},
            headers={"Idempotency-Key": "same-key"},
        )
        conflict = await client.post(
            "/api/runs",
            json={"repository": str(other)},
            headers={"Idempotency-Key": "same-key"},
        )

    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "idempotency_conflict"


@pytest.mark.asyncio
async def test_event_stream_contains_ordered_sse_records(api_app) -> None:
    repository = api_app.state.test_repository
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client:
        created = await client.post(
            "/api/runs",
            json={"repository": str(repository)},
            headers={"Idempotency-Key": "stream-run"},
        )
        response = await client.get(f"/api/runs/{created.json()['run']['id']}/events/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "id: 1" in response.text
    assert "event: run_event" in response.text
    assert '"kind":"approval_required"' in response.text
    assert response.text.index("id: 1\n") < response.text.index("id: 7\n")


@pytest.mark.asyncio
async def test_repository_inspection_endpoint_uses_boundary(api_app, tmp_path) -> None:
    repository = api_app.state.test_repository
    outside = tmp_path.parent
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client:
        accepted = await client.post(
            "/api/repositories/inspect", json={"repository": str(repository)}
        )
        rejected = await client.post("/api/repositories/inspect", json={"repository": str(outside)})

    assert accepted.status_code == 200
    assert accepted.json()["head"]
    assert rejected.status_code == 400
    assert rejected.json()["detail"]["code"] == "repository_invalid"
