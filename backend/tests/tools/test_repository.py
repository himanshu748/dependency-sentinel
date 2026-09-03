import subprocess
from pathlib import Path

import pytest


def _repository_api():
    try:
        from app.tools.repository import RepositoryBoundaryError, inspect_repository
    except ImportError:
        pytest.fail("repository inspection tool is not implemented")
    return RepositoryBoundaryError, inspect_repository


def _create_repository(path: Path) -> None:
    path.mkdir(parents=True)
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", path], check=True)
    subprocess.run(["git", "-C", path, "add", "README.md"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            path,
            "-c",
            "user.name=Dependency Sentinel Tests",
            "-c",
            "user.email=tests@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )


def test_repository_inspector_reports_clean_head_without_modifying_checkout(tmp_path: Path) -> None:
    """Catch inspection that mutates the repository or loses its Git identity."""
    _, inspect_repository = _repository_api()
    root = tmp_path / "allowed"
    repository = root / "project"
    _create_repository(repository)
    before = subprocess.run(
        ["git", "-C", repository, "status", "--porcelain=v1"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    result = inspect_repository(repository, allowed_root=root)

    after = subprocess.run(
        ["git", "-C", repository, "status", "--porcelain=v1"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    expected_head = subprocess.run(
        ["git", "-C", repository, "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert result.path == repository.resolve()
    assert result.head == expected_head
    assert result.dirty is False
    assert before == after == ""


def test_repository_inspector_rejects_paths_outside_allowed_root(tmp_path: Path) -> None:
    """Catch a path traversal that gives the agent access to an unrelated checkout."""
    RepositoryBoundaryError, inspect_repository = _repository_api()
    root = tmp_path / "allowed"
    outside = tmp_path / "outside"
    _create_repository(outside)
    root.mkdir()

    with pytest.raises(RepositoryBoundaryError, match="outside the configured root"):
        inspect_repository(outside, allowed_root=root)


def test_repository_inspector_rejects_symlink_escape(tmp_path: Path) -> None:
    """Catch a symlink inside the root that resolves to an outside repository."""
    RepositoryBoundaryError, inspect_repository = _repository_api()
    root = tmp_path / "allowed"
    outside = tmp_path / "outside"
    _create_repository(outside)
    root.mkdir()
    (root / "linked-project").symlink_to(outside, target_is_directory=True)

    with pytest.raises(RepositoryBoundaryError, match="outside the configured root"):
        inspect_repository(root / "linked-project", allowed_root=root)
