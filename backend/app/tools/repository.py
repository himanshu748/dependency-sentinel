import subprocess
from pathlib import Path

from app.domain.models import RepositorySnapshot


class RepositoryBoundaryError(ValueError):
    """Raised when a repository is invalid or outside the configured root."""


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "Git command failed"
        raise RepositoryBoundaryError(detail)
    return result.stdout.strip()


def inspect_repository(path: Path, *, allowed_root: Path) -> RepositorySnapshot:
    root = Path(allowed_root).resolve(strict=True)
    repository = Path(path).resolve(strict=True)
    try:
        repository.relative_to(root)
    except ValueError as error:
        raise RepositoryBoundaryError("repository is outside the configured root") from error

    if not repository.is_dir():
        raise RepositoryBoundaryError("repository path is not a directory")

    top_level = Path(_git(repository, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top_level != repository:
        raise RepositoryBoundaryError("path must identify the repository root")

    head = _git(repository, "rev-parse", "HEAD")
    branch = _git(repository, "branch", "--show-current") or "detached"
    dirty = bool(_git(repository, "status", "--porcelain=v1"))
    return RepositorySnapshot(path=repository, head=head, branch=branch, dirty=dirty)
