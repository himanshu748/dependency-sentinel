from pathlib import Path

import pytest


def _storage_api():
    try:
        from app.domain.models import ApprovalChoice, RunStatus
        from app.storage.sqlite import ApprovalConflict, SQLiteStore
    except ImportError:
        pytest.fail("SQLite run storage is not implemented")
    return ApprovalChoice, RunStatus, ApprovalConflict, SQLiteStore


def test_run_lifecycle_is_persisted_across_store_instances(tmp_path: Path) -> None:
    """Catch an in-memory-only implementation that loses paused agent work."""
    _, RunStatus, _, SQLiteStore = _storage_api()
    database_path = tmp_path / "runs.sqlite3"
    store = SQLiteStore(database_path)
    store.initialize()

    created = store.create_run(
        task_type="dependency_upgrade",
        input_summary="fixture repository",
        run_id="run-001",
    )
    store.transition_run(created.id, RunStatus.RUNNING)

    reopened = SQLiteStore(database_path)
    loaded = reopened.get_run(created.id)

    assert loaded is not None
    assert loaded.id == "run-001"
    assert loaded.status is RunStatus.RUNNING
    assert loaded.task_type == "dependency_upgrade"
    assert loaded.input_summary == "fixture repository"
    assert loaded.created_at.tzinfo is not None


def test_event_idempotency_prevents_duplicate_timeline_entries(tmp_path: Path) -> None:
    """Catch duplicate events when an idempotent tool result is retried."""
    _, _, _, SQLiteStore = _storage_api()
    store = SQLiteStore(tmp_path / "events.sqlite3")
    store.initialize()
    store.create_run("dependency_upgrade", "fixture", run_id="run-002")

    first = store.append_event(
        "run-002",
        kind="tool_result",
        summary="manifest scanned",
        payload={"dependencies": 4},
        idempotency_key="manifest-scan-1",
    )
    repeated = store.append_event(
        "run-002",
        kind="tool_result",
        summary="this retry must not replace the original",
        payload={"dependencies": 99},
        idempotency_key="manifest-scan-1",
    )

    events = store.list_events("run-002")
    assert first == repeated
    assert len(events) == 1
    assert events[0].sequence == 1
    assert events[0].payload == {"dependencies": 4}


def test_conflicting_approval_decision_is_rejected(tmp_path: Path) -> None:
    """Catch a retry that changes a recorded human decision."""
    ApprovalChoice, _, ApprovalConflict, SQLiteStore = _storage_api()
    store = SQLiteStore(tmp_path / "approvals.sqlite3")
    store.initialize()
    store.create_run("dependency_upgrade", "fixture", run_id="run-003")

    first = store.record_approval(
        "run-003", approval_id="prepare-pr", choice=ApprovalChoice.APPROVED
    )
    repeated = store.record_approval(
        "run-003", approval_id="prepare-pr", choice=ApprovalChoice.APPROVED
    )

    assert first == repeated
    assert store.has_approval("run-003", "prepare-pr") is True
    with pytest.raises(ApprovalConflict, match="already recorded"):
        store.record_approval("run-003", approval_id="prepare-pr", choice=ApprovalChoice.REJECTED)
