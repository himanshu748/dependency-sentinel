import re
import subprocess
from hashlib import sha256
from pathlib import Path
from types import TracebackType
from uuid import uuid4


class WorktreeError(RuntimeError):
    """Raised when an isolated worktree cannot be created or removed safely."""


_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "Git command failed"
        raise WorktreeError(detail)
    return completed.stdout.strip()


def tracked_worktree_fingerprint(workspace: Path) -> str:
    """Bind tracked source, index and detached HEAD; ordinary test caches are excluded."""
    state = [
        _git(workspace, "rev-parse", "HEAD"),
        _git(workspace, "ls-files", "--stage"),
        _git(workspace, "diff", "--binary", "--no-ext-diff", "--no-textconv", "HEAD", "--"),
    ]
    return sha256("\0".join(state).encode()).hexdigest()


def verify_staged_scope(workspace: Path, *, revision: str, changed_files: list[Path]) -> None:
    changed = set(_git(workspace, "diff", "--name-only", "--no-renames", "HEAD", "--").splitlines())
    if _git(workspace, "rev-parse", "HEAD") != revision:
        raise WorktreeError("Staged worktree moved away from the captured source revision")
    if not changed or not changed.issubset({str(path) for path in changed_files}):
        raise WorktreeError("Staged worktree includes changes outside the proposed patch")


class DisposableWorktree:
    def __init__(
        self,
        source: Path,
        workspace_root: Path,
        *,
        run_id: str | None = None,
        revision: str | None = None,
    ) -> None:
        self.source = Path(source).resolve(strict=True)
        self.workspace_root = Path(workspace_root)
        self.run_id = run_id or f"run-{uuid4().hex[:12]}"
        if not _RUN_ID.fullmatch(self.run_id):
            raise WorktreeError("run id contains unsupported characters")
        self.revision = revision or _git(self.source, "rev-parse", "HEAD")
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", self.revision):
            raise WorktreeError("worktree revision must be a full captured commit SHA")
        self.path: Path | None = None

    def __enter__(self) -> Path:
        top_level = Path(_git(self.source, "rev-parse", "--show-toplevel")).resolve(strict=True)
        if top_level != self.source:
            raise WorktreeError("source must identify the repository root")

        self.workspace_root.mkdir(parents=True, exist_ok=True)
        root = self.workspace_root.resolve(strict=True)
        destination = (root / self.run_id).resolve(strict=False)
        if destination.parent != root:
            raise WorktreeError("worktree destination escaped its configured root")
        if destination.exists():
            raise WorktreeError("worktree destination already exists")

        _git(self.source, "worktree", "add", "--detach", str(destination), self.revision)
        self.path = destination
        return destination

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self.path is None:
            return
        root = self.workspace_root.resolve(strict=True)
        destination = self.path.resolve(strict=False)
        if destination.parent != root:
            raise WorktreeError("refusing to remove a worktree outside its configured root")
        _git(self.source, "worktree", "remove", "--force", str(destination))
        _git(self.source, "worktree", "prune")
        self.path = None
