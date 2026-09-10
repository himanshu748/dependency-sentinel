import subprocess
from pathlib import Path

from app.tools.worktree import DisposableWorktree


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def seeded_repository(path: Path) -> Path:
    path.mkdir()
    git(path, "init", "-q")
    git(path, "config", "user.email", "sentinel@example.test")
    git(path, "config", "user.name", "Dependency Sentinel")
    (path / "pyproject.toml").write_text('[project]\nname = "fixture"\n')
    git(path, "add", "pyproject.toml")
    git(path, "commit", "-qm", "fixture")
    return path


def test_disposable_worktree_never_changes_source_checkout(tmp_path: Path) -> None:
    source = seeded_repository(tmp_path / "source")
    workspace_root = tmp_path / "workspaces"
    before_head = git(source, "rev-parse", "HEAD")
    before_status = git(source, "status", "--porcelain=v1")

    with DisposableWorktree(source, workspace_root) as workspace:
        (workspace / "pyproject.toml").write_text('[project]\nname = "changed"\n')
        assert (source / "pyproject.toml").read_text() == '[project]\nname = "fixture"\n'
        workspace_path = workspace

    assert not workspace_path.exists()
    assert git(source, "rev-parse", "HEAD") == before_head
    assert git(source, "status", "--porcelain=v1") == before_status


def test_disposable_worktree_uses_validated_destination(tmp_path: Path) -> None:
    source = seeded_repository(tmp_path / "source")
    workspace_root = tmp_path / "workspaces"

    with DisposableWorktree(source, workspace_root, run_id="run-123") as workspace:
        assert workspace.parent.resolve() == workspace_root.resolve()
        assert workspace.name == "run-123"


def test_worktree_stays_at_captured_commit_when_head_moves(tmp_path: Path) -> None:
    source = seeded_repository(tmp_path / "source")
    revision = git(source, "rev-parse", "HEAD")
    staged = DisposableWorktree(source, tmp_path / "workspaces", revision=revision)
    (source / "pyproject.toml").write_text('[project]\nname = "later"\n')
    git(source, "commit", "-qam", "later source commit")
    assert git(source, "rev-parse", "HEAD") != revision
    with staged as workspace:
        assert git(workspace, "rev-parse", "HEAD") == revision
        assert 'name = "fixture"' in (workspace / "pyproject.toml").read_text()
    assert 'name = "later"' in (source / "pyproject.toml").read_text()
