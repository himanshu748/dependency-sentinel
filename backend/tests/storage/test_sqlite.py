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


def paused_store(tmp_path):
    _, RunStatus, _, SQLiteStore = _storage_api()
    store = SQLiteStore(tmp_path / "atomic.sqlite3")
    store.initialize()
    store.create_run("dependency_upgrade", "controlled fixture", run_id="atomic")
    store.transition_run("atomic", RunStatus.RUNNING)
    store.append_event(
        "atomic",
        kind="approval_required",
        summary="Review required",
        payload={"approval_id": "apply-upgrade"},
        idempotency_key="atomic:approval_required",
    )
    store.transition_run("atomic", RunStatus.WAITING_FOR_APPROVAL)
    return store


@pytest.mark.parametrize("choice_value", ["approved", "rejected"])
def test_approval_failure_rolls_back_decision_events_and_status_across_connections(
    tmp_path, monkeypatch, choice_value
):
    ApprovalChoice, RunStatus, _, SQLiteStore = _storage_api()
    store = paused_store(tmp_path)
    original = store._append_event

    def interrupted(*args, **kwargs):
        original(*args, **kwargs)
        raise OSError("injected interruption after event insert")

    monkeypatch.setattr(store, "_append_event", interrupted)
    choice = ApprovalChoice(choice_value)
    with pytest.raises(OSError, match="injected interruption"):
        store.complete_approval("atomic", approval_id="apply-upgrade", choice=choice)

    reopened = SQLiteStore(store.database_path)
    assert reopened.get_run("atomic").status is RunStatus.WAITING_FOR_APPROVAL
    assert reopened.get_approval("atomic", "apply-upgrade") is None
    assert [event.kind for event in reopened.list_events("atomic")] == ["approval_required"]
    completed = reopened.complete_approval("atomic", approval_id="apply-upgrade", choice=choice)
    expected = RunStatus.COMPLETED if choice is ApprovalChoice.APPROVED else RunStatus.CANCELLED
    assert completed.status is expected
    again = SQLiteStore(store.database_path)
    assert (
        again.complete_approval("atomic", approval_id="apply-upgrade", choice=choice) == completed
    )
    assert len(again.list_events("atomic")) == (3 if choice is ApprovalChoice.APPROVED else 2)


def test_legacy_interrupted_approval_can_resume_without_duplicate_events(tmp_path):
    ApprovalChoice, RunStatus, _, SQLiteStore = _storage_api()
    store = paused_store(tmp_path)
    store.record_approval("atomic", approval_id="apply-upgrade", choice=ApprovalChoice.APPROVED)
    store.transition_run("atomic", RunStatus.RUNNING, approval_recorded=True)
    store.append_event(
        "atomic",
        kind="approval_recorded",
        summary="Already approved",
        payload={"approval_id": "apply-upgrade", "choice": "approved"},
        idempotency_key="atomic:approval_recorded",
    )
    reopened = SQLiteStore(store.database_path)
    result = reopened.complete_approval(
        "atomic", approval_id="apply-upgrade", choice=ApprovalChoice.APPROVED
    )
    assert result.status is RunStatus.COMPLETED
    assert [event.kind for event in reopened.list_events("atomic")] == [
        "approval_required",
        "approval_recorded",
        "report_completed",
    ]


def test_conflicting_decisions_from_independent_connections_have_one_winner(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    ApprovalChoice, RunStatus, ApprovalConflict, SQLiteStore = _storage_api()
    store = paused_store(tmp_path)

    def decide(choice):
        try:
            return SQLiteStore(store.database_path).complete_approval(
                "atomic", approval_id="apply-upgrade", choice=choice
            )
        except ApprovalConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(decide, [ApprovalChoice.APPROVED, ApprovalChoice.REJECTED]))
    assert sum(result is not None for result in results) == 1
    current = SQLiteStore(store.database_path)
    assert current.get_run("atomic").status in {RunStatus.COMPLETED, RunStatus.CANCELLED}
    events = current.list_events("atomic")
    assert len({event.kind for event in events}) == len(events)
