import pytest

import app.agent.orchestrator as orchestration
from app.domain.models import ApprovalChoice, CommandResult, RunStatus
from app.tools.command_runner import AllowedCommand
from app.tools.python_manifest import scan_python_manifest
from tests.agent.test_upgrade_workflow import PassingRunner, git, seeded_repository, workflow


def test_selection_staging_and_validation_use_commit_captured_before_head_moves(
    tmp_path, monkeypatch
):
    source = seeded_repository(tmp_path)
    revision = git(source, "rev-parse", "HEAD")
    committed_manifest = (source / "pyproject.toml").read_text()
    original_inspect = orchestration.inspect_repository

    def inspect_then_move(*args, **kwargs):
        snapshot = original_inspect(*args, **kwargs)
        (source / "pyproject.toml").write_text(committed_manifest.replace("3.1.4", "0.0.1"))
        git(source, "commit", "-qam", "controlled concurrent HEAD move")
        return snapshot

    class SnapshotRunner(PassingRunner):
        def execute(self, request, *, cwd):
            assert git(cwd, "rev-parse", "HEAD") == revision
            assert "3.1.5" in (cwd / "pyproject.toml").read_text()
            return super().execute(request, cwd=cwd)

    service, store = workflow(tmp_path, runner=SnapshotRunner())
    monkeypatch.setattr(orchestration, "inspect_repository", inspect_then_move)
    outcome = service.start(source, run_id="pinned-source")
    assert outcome.run.status is RunStatus.WAITING_FOR_APPROVAL
    assert outcome.candidate.current_version == "3.1.4"
    assert git(source, "rev-parse", "HEAD") != revision
    assert "0.0.1" in (source / "pyproject.toml").read_text()
    for event in store.list_events(outcome.run.id):
        if event.kind in {
            "manifest_scanned",
            "candidate_selected",
            "upgrade_staged",
            "validation_completed",
        }:
            assert event.payload["source_revision"] == revision


def test_commit_manifest_read_ignores_later_working_file_changes(tmp_path):
    source = seeded_repository(tmp_path)
    revision = git(source, "rev-parse", "HEAD")
    before = scan_python_manifest(source, revision=revision)
    (source / "pyproject.toml").write_text("not valid TOML")
    assert scan_python_manifest(source, revision=revision) == before


@pytest.mark.parametrize("filename", ["pyproject.toml", "uv.lock", "new-untracked.txt"])
def test_dirty_input_is_rejected_without_changes_or_command_execution(tmp_path, filename):
    source = seeded_repository(tmp_path)
    target = source / filename
    target.write_text("local work to preserve")
    service, store = workflow(tmp_path, runner=PassingRunner())
    with pytest.raises(ValueError, match="Commit or stash"):
        service.start(source, run_id="dirty-source")
    assert target.read_text() == "local work to preserve"
    assert not (tmp_path / "workspaces").exists()
    assert store.list_events("dirty-source") == []


def test_uncommitted_lockfile_is_not_used_as_snapshot_input(tmp_path):
    source = seeded_repository(tmp_path)
    git(source, "rm", "--cached", "uv.lock")
    git(source, "commit", "-qm", "stop tracking fixture lockfile")
    with pytest.raises(ValueError, match="uv.lock must be tracked"):
        scan_python_manifest(source, revision=git(source, "rev-parse", "HEAD"))


@pytest.mark.parametrize("filename", ["uv.lock", "tests/test_validated_version.py"])
def test_validation_that_changes_tracked_source_cannot_reach_approval(tmp_path, filename):
    source = seeded_repository(tmp_path)

    class MutatingRunner(PassingRunner):
        def execute(self, request, *, cwd):
            (cwd / filename).write_text("changed during synthetic validation")
            return super().execute(request, cwd=cwd)

    service, store = workflow(tmp_path, runner=MutatingRunner())
    outcome = service.start(source, run_id="changed-during-test")
    assert outcome.run.status is RunStatus.FAILED
    assert outcome.approval_id is None
    validation = next(
        e for e in store.list_events(outcome.run.id) if e.kind == "validation_completed"
    )
    assert validation.payload["staged_files_unchanged"] is False


def test_repository_config_cannot_hide_untracked_input_from_dirty_guard(tmp_path):
    source = seeded_repository(tmp_path)
    git(source, "config", "status.showUntrackedFiles", "no")
    (source / "uncommitted.txt").write_text("local work")
    service, _ = workflow(tmp_path, runner=PassingRunner())
    with pytest.raises(ValueError, match="Commit or stash"):
        service.start(source, run_id="hidden-untracked")


@pytest.mark.parametrize("extra_change", [False, True])
def test_saved_resolution_command_is_bound_and_extra_tracked_changes_are_blocked(
    tmp_path, extra_change
):
    source = seeded_repository(tmp_path)

    class ControlledResolver(PassingRunner):
        def execute(self, request, *, cwd):
            if request.name is AllowedCommand.UV_LOCK:
                lock = cwd / "uv.lock"
                lock.write_text(lock.read_text().replace("3.1.4", "3.1.5"))
                if extra_change:
                    (cwd / "tests/test_validated_version.py").write_text("unexpected change")
                return CommandResult(
                    command=["uv", "lock", "--upgrade-package", "jinja2"],
                    exit_code=0,
                    stdout="Controlled resolver result",
                    stderr="",
                    duration_seconds=0.1,
                )
            return super().execute(request, cwd=cwd)

    service, store = workflow(tmp_path, runner=ControlledResolver())
    service.resolve_lock = True
    if extra_change:
        with pytest.raises(RuntimeError, match="outside the proposed patch"):
            service.start(source, run_id="unexpected-resolution-change")
        return
    outcome = service.start(source, run_id="controlled-resolution")
    service.decide(outcome.run.id, approval_id="apply-upgrade", choice=ApprovalChoice.APPROVED)
    receipt, _ = store.approved_export(outcome.run.id)
    assert receipt["source"]["execution"]["lock_resolution"] is True
    assert receipt["commands"][0]["command"] == ["uv", "lock", "--upgrade-package", "jinja2"]
    assert receipt["commands"][0]["stdout"] == "Controlled resolver result"
    assert len(receipt["commands"]) == 2
