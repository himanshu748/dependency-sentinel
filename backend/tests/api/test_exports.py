import json
import sqlite3
from hashlib import sha256

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.models import RunStatus
from app.domain.review import review_digest, review_material
from app.storage.sqlite import SQLiteStore


async def create_review(client, app, *, approve=True):
    response = await client.post(
        "/api/runs",
        json={"repository": str(app.state.test_repository)},
        headers={"Idempotency-Key": "export-controlled-review"},
    )
    assert response.status_code == 201, response.text
    run_id = response.json()["run"]["id"]
    if approve:
        decision = await client.post(
            f"/api/runs/{run_id}/approvals",
            json={"approval_id": "apply-upgrade", "choice": "approved"},
        )
        assert decision.status_code == 200, decision.text
    return run_id


def edit_event(store, run_id, kind, update):
    with sqlite3.connect(store.database_path) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM events WHERE run_id = ? AND kind = ?", (run_id, kind)
            ).fetchone()[0]
        )
        update(payload)
        connection.execute(
            "UPDATE events SET payload = ? WHERE run_id = ? AND kind = ?",
            (json.dumps(payload), run_id, kind),
        )


@pytest.mark.asyncio
async def test_approved_exports_are_server_generated_and_survive_source_changes_and_restart(
    api_app,
):
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
        run_id = await create_review(client, api_app)
        patch = await client.get(f"/api/runs/{run_id}/exports/patch")
        receipt = await client.get(f"/api/runs/{run_id}/exports/receipt")
        assert patch.status_code == receipt.status_code == 200
        record = receipt.json()
        assert record["patch"]["sha256"] == sha256(patch.content).hexdigest()
        assert record["source"]["head"] == record["validation"]["source_revision"]
        assert record["source"]["execution"] == {
            "model_mode": "fixture",
            "evidence_mode": "fixture",
            "lock_resolution": False,
        }
        assert record["evidence"]["release"]["source"]["retrieved_at"]
        assert record["evidence"]["advisories"][0]["source"]["retrieved_at"]
        assert record["validation"]["results"][0] == {
            "command": ["python", "-m", "pytest", "-q"],
            "exit_code": 0,
            "stdout": "2 passed",
            "stderr": "",
            "duration_seconds": 0.1,
            "timed_out": False,
        }
        assert record["approval"]["choice"] == "approved"
        assert record["approval"]["created_at"]
        assert record["source_checkout_modified"] is False
        assert patch.headers["content-disposition"] == f'attachment; filename="{run_id}.patch"'
        assert receipt.headers["cache-control"] == "no-store"
        (api_app.state.test_repository / "uv.lock").write_text("later local work")
        reopened = SQLiteStore(api_app.state.store.database_path)
        saved_receipt, saved_patch = reopened.approved_export(run_id)
        assert saved_receipt == record
        assert saved_patch.encode() == patch.content
        assert (await client.get(f"/api/runs/{run_id}/exports/receipt")).content == receipt.content


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal", ["waiting_for_approval", "failed", "cancelled", "running"])
async def test_unapproved_failed_rejected_and_incomplete_runs_cannot_export(api_app, terminal):
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
        run_id = await create_review(client, api_app, approve=False)
        with sqlite3.connect(api_app.state.store.database_path) as connection:
            connection.execute("UPDATE runs SET status = ? WHERE id = ?", (terminal, run_id))
        for kind in ("patch", "receipt"):
            result = await client.get(f"/api/runs/{run_id}/exports/{kind}")
            assert result.status_code == 409
            assert result.json()["detail"]["code"] == "review_not_exportable"
        assert (await client.get(f"/api/runs/{run_id}")).json()["status"] == terminal


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind,update",
    [
        ("upgrade_staged", lambda p: p.update(diff=p["diff"] + "changed")),
        ("upgrade_staged", lambda p: p.update(diff="")),
        ("validation_completed", lambda p: p.update(results=[])),
        ("validation_completed", lambda p: p["results"][0].update(exit_code=1)),
        ("validation_completed", lambda p: p["results"][0].update(timed_out=True)),
        ("validation_completed", lambda p: p["results"][0].pop("timed_out")),
        ("validation_completed", lambda p: p["results"][0].update(command=[])),
        ("validation_completed", lambda p: p["results"][0].update(exit_code="0")),
        ("validation_completed", lambda p: p.update(source_revision="b" * 40)),
        ("candidate_selected", lambda p: p.update(target_version="99.0.0")),
        ("candidate_selected", lambda p: p.update(target_version="not-a-version")),
        ("upgrade_staged", lambda p: p.update(changed_files=None)),
        ("evidence_collected", lambda p: p["release"]["source"].update(excerpt="changed")),
        ("repository_inspected", lambda p: p.pop("provenance_version")),
        ("approval_required", lambda p: p.update(review_sha256="0" * 64)),
        ("approval_recorded", lambda p: p.update(review_sha256="0" * 64)),
        ("approval_recorded", lambda p: p.update(approved_at="later")),
        ("report_completed", lambda p: p.update(source_checkout_modified=True)),
    ],
)
async def test_tampered_or_incomplete_records_block_both_exports(api_app, kind, update):
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
        run_id = await create_review(client, api_app)
        edit_event(api_app.state.store, run_id, kind, update)
        for export in ("patch", "receipt"):
            result = await client.get(f"/api/runs/{run_id}/exports/{export}")
            assert result.status_code == 409, result.text


@pytest.mark.asyncio
async def test_changed_record_cannot_be_approved_and_leaves_no_partial_decision(api_app):
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
        run_id = await create_review(client, api_app, approve=False)
        edit_event(
            api_app.state.store, run_id, "validation_completed", lambda p: p.update(results=[])
        )
        result = await client.post(
            f"/api/runs/{run_id}/approvals",
            json={"approval_id": "apply-upgrade", "choice": "approved"},
        )
        assert result.status_code == 409
        assert api_app.state.store.get_approval(run_id, "apply-upgrade") is None
        assert api_app.state.store.get_run(run_id).status is RunStatus.WAITING_FOR_APPROVAL


@pytest.mark.asyncio
async def test_missing_approval_and_legacy_provenance_are_not_exportable_but_remain_viewable(
    api_app,
):
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
        run_id = await create_review(client, api_app)
        with sqlite3.connect(api_app.state.store.database_path) as connection:
            connection.execute("DELETE FROM approvals WHERE run_id = ?", (run_id,))
        assert (await client.get(f"/api/runs/{run_id}/exports/receipt")).status_code == 409
        assert (await client.get(f"/api/runs/{run_id}")).status_code == 200
        assert (await client.get("/api/runs/absent/exports/patch")).status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("approved", [False, True], ids=["awaiting-approval", "already-approved"])
@pytest.mark.parametrize(
    "fingerprint",
    [
        pytest.param("missing", id="legacy-missing"),
        pytest.param(None, id="null"),
        pytest.param(42, id="non-string"),
        pytest.param("a" * 63, id="short"),
        pytest.param("a" * 65, id="long"),
        pytest.param("g" * 64, id="non-hex"),
    ],
)
async def test_missing_or_malformed_tree_fingerprint_blocks_a_matching_saved_record(
    api_app, approved, fingerprint
):
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://testserver"
    ) as client:
        run_id = await create_review(client, api_app, approve=approved)
        store = api_app.state.store
        material = review_material(run_id, store.list_events(run_id))
        validation_event = next(
            event for event in material["events"] if event["kind"] == "validation_completed"
        )

        def replace_fingerprint(payload):
            if fingerprint == "missing":
                payload.pop("tracked_worktree_sha256")
            else:
                payload["tracked_worktree_sha256"] = fingerprint

        replace_fingerprint(validation_event["payload"])
        edit_event(store, run_id, "validation_completed", replace_fingerprint)
        # Model a consistently bound older record, so rejection cannot be caused
        # merely by changing an event without updating its saved digest.
        matching_digest = review_digest(material)
        binding_kinds = ["approval_required"]
        if approved:
            binding_kinds.extend(["approval_recorded", "report_completed"])
        for kind in binding_kinds:
            edit_event(
                store, run_id, kind, lambda payload: payload.update(review_sha256=matching_digest)
            )
        saved_events = store.list_events(run_id)
        assert (
            next(
                event.model_dump(mode="json")
                for event in saved_events
                if event.kind == "validation_completed"
            )
            == validation_event
        )
        assert all(
            event.payload["review_sha256"] == matching_digest
            for event in saved_events
            if event.kind in binding_kinds
        )

        if not approved:
            decision = await client.post(
                f"/api/runs/{run_id}/approvals",
                json={"approval_id": "apply-upgrade", "choice": "approved"},
            )
            assert decision.status_code == 409
            assert "tracked-worktree fingerprint" in decision.json()["detail"]["message"]
            assert store.get_approval(run_id, "apply-upgrade") is None
        for kind in ("patch", "receipt"):
            result = await client.get(f"/api/runs/{run_id}/exports/{kind}")
            assert result.status_code == 409
            assert result.json()["detail"]["code"] == "review_not_exportable"
            if approved:
                assert "tracked-worktree fingerprint" in result.json()["detail"]["message"]
        visible = await client.get(f"/api/runs/{run_id}")
        assert visible.status_code == 200
        assert visible.json()["status"] == ("completed" if approved else "waiting_for_approval")
        assert store.list_events(run_id) == saved_events
