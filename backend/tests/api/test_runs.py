import asyncio
from threading import Event

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_create_poll_and_idempotently_retry_run(api_app) -> None:
    repository = api_app.state.test_repository
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
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
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
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
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
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
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
        accepted = await client.post(
            "/api/repositories/inspect", json={"repository": str(repository)}
        )
        rejected = await client.post("/api/repositories/inspect", json={"repository": str(outside)})

    assert accepted.status_code == 200
    assert accepted.json()["head"]
    assert rejected.status_code == 400
    assert rejected.json()["detail"]["code"] == "repository_invalid"


@pytest.mark.asyncio
async def test_failed_scan_persists_recovery_reason(api_app, tmp_path) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/runs",
            json={"repository": str(tmp_path / "missing")},
            headers={"Idempotency-Key": "missing-repository"},
        )
        runs = (await client.get("/api/runs")).json()
        events = (await client.get(f"/api/runs/{runs[0]['id']}/events")).json()
    assert response.status_code == 400
    assert runs[0]["status"] == "failed"
    assert events[-1]["kind"] == "run_failed"
    assert events[-1]["payload"]["message"]


@pytest.mark.asyncio
async def test_scan_keeps_health_responsive_and_rejects_parallel_execution(api_app) -> None:
    started, release = Event(), Event()
    original = api_app.state.workflow.command_runner

    class BoundedRunner:
        def execute(self, request, *, cwd):
            started.set()
            assert release.wait(timeout=5)
            return original.execute(request, cwd=cwd)

    api_app.state.workflow.command_runner = BoundedRunner()
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
        request = {"repository": str(api_app.state.test_repository)}
        first = asyncio.create_task(
            client.post("/api/runs", json=request, headers={"Idempotency-Key": "active-review"})
        )
        try:
            assert await asyncio.to_thread(started.wait, 3)
            health = await asyncio.wait_for(client.get("/api/health"), timeout=1)
            second = await client.post(
                "/api/runs", json=request, headers={"Idempotency-Key": "another-review"}
            )
            assert health.status_code == 200
            assert second.status_code == 409
            assert second.json()["detail"]["code"] == "scan_in_progress"
        finally:
            release.set()
            completed = await first
        assert completed.status_code == 201


@pytest.mark.asyncio
async def test_unexpected_provider_failure_is_saved_without_exposing_exception(api_app) -> None:
    class BrokenSelector:
        def select(self, *args):
            raise TypeError("private provider credential detail")

    api_app.state.workflow.selector = BrokenSelector()
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/runs",
            json={"repository": str(api_app.state.test_repository)},
            headers={"Idempotency-Key": "provider-crash"},
        )
        runs = (await client.get("/api/runs")).json()
        events = (await client.get(f"/api/runs/{runs[0]['id']}/events")).json()
    assert response.status_code == 500
    assert "credential" not in response.text
    assert runs[0]["status"] == "failed"
    assert events[-1]["kind"] == "run_failed"
    assert "credential" not in str(events)
