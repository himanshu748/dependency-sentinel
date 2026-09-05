import shutil
import subprocess
from pathlib import Path

import pytest

from app.agent.orchestrator import DependencyUpgradeWorkflow, FixtureCandidateSelector
from app.domain.models import CommandResult, RunStatus
from app.evidence.fixtures import FixtureEvidenceStore
from app.storage.sqlite import SQLiteStore

ROOT = Path(__file__).parents[3]


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def seeded_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "source"
    shutil.copytree(ROOT / "fixtures" / "vulnerable-python-project", repository)
    git(repository, "init", "-q")
    git(repository, "config", "user.email", "sentinel@example.test")
    git(repository, "config", "user.name", "Dependency Sentinel")
    git(repository, "add", ".")
    git(repository, "commit", "-qm", "seed vulnerable fixture")
    return repository


class PassingRunner:
    def execute(self, request: object, *, cwd: Path) -> CommandResult:
        return CommandResult(
            command=["python", "-m", "pytest", "-q"],
            exit_code=0,
            stdout="2 passed",
            stderr="",
            duration_seconds=0.1,
        )


class FailingRunner:
    def execute(self, request: object, *, cwd: Path) -> CommandResult:
        return CommandResult(
            command=["python", "-m", "pytest", "-q"],
            exit_code=1,
            stdout="1 failed",
            stderr="",
            duration_seconds=0.1,
        )


def workflow(tmp_path: Path, *, runner: object) -> tuple[DependencyUpgradeWorkflow, SQLiteStore]:
    store = SQLiteStore(tmp_path / "runs.sqlite3")
    store.initialize()
    evidence = FixtureEvidenceStore(ROOT / "fixtures" / "evidence")
    return (
        DependencyUpgradeWorkflow(
            store=store,
            allowed_repository_root=tmp_path,
            workspace_root=tmp_path / "workspaces",
            selector=FixtureCandidateSelector(),
            advisory_provider=evidence,
            release_provider=evidence,
            command_runner=runner,
        ),
        store,
    )


def test_workflow_selects_validates_and_pauses_without_mutating_source(tmp_path: Path) -> None:
    repository = seeded_repository(tmp_path)
    before_head = git(repository, "rev-parse", "HEAD")
    before_status = git(repository, "status", "--porcelain=v1")
    service, store = workflow(tmp_path, runner=PassingRunner())

    outcome = service.start(repository, run_id="run-safe-upgrade")

    assert outcome.run.status is RunStatus.WAITING_FOR_APPROVAL
    assert outcome.candidate.package == "jinja2"
    assert outcome.candidate.target_version == "3.1.5"
    assert outcome.approval_id == "apply-upgrade"
    assert git(repository, "rev-parse", "HEAD") == before_head
    assert git(repository, "status", "--porcelain=v1") == before_status
    events = store.list_events(outcome.run.id)
    assert [event.kind for event in events] == [
        "repository_inspected",
        "manifest_scanned",
        "candidate_selected",
        "evidence_collected",
        "upgrade_staged",
        "validation_completed",
        "approval_required",
    ]
    assert events[-1].payload["approval_id"] == "apply-upgrade"
    assert events[-2].payload["passed"] is True
    assert "CVE-2024-56326" in events[3].payload["advisory_ids"]


def test_validation_failure_stops_before_approval(tmp_path: Path) -> None:
    repository = seeded_repository(tmp_path)
    service, store = workflow(tmp_path, runner=FailingRunner())

    outcome = service.start(repository, run_id="run-failing-upgrade")

    assert outcome.run.status is RunStatus.FAILED
    assert outcome.approval_id is None
    assert "approval_required" not in [event.kind for event in store.list_events(outcome.run.id)]


@pytest.mark.parametrize(
    "changed",
    [
        {"advisory_identifier": "invented-advisory"},
        {"current_version": "0.0.1"},
        {"target_version": "99.0.0"},
    ],
)
def test_untrusted_candidate_cannot_reach_worktree(tmp_path, changed):
    repository = seeded_repository(tmp_path)
    service, store = workflow(tmp_path, runner=PassingRunner())

    class InvalidSelector:
        def select(self, repository, manifest, advisory_provider):
            candidate = FixtureCandidateSelector().select(repository, manifest, advisory_provider)
            return candidate.model_copy(update=changed)

    service.selector = InvalidSelector()
    with pytest.raises(ValueError):
        service.start(repository, run_id="run-invalid")
    assert "upgrade_staged" not in [event.kind for event in store.list_events("run-invalid")]
    assert git(repository, "status", "--porcelain=v1") == ""
