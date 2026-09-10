import difflib
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Protocol

from packaging.version import Version
from strands import tool

from app.agent.fixture_model import fixture_advice
from app.domain.models import (
    AdvisoryEvidence,
    AgentRun,
    ApprovalChoice,
    CandidateSelection,
    PythonManifest,
    ReleaseEvidence,
    RunStatus,
    WorkflowOutcome,
)
from app.domain.review import review_digest, review_material
from app.storage.sqlite import ApprovalConflict, SQLiteStore
from app.tools.command_runner import AllowedCommand, CommandRequest
from app.tools.python_manifest import scan_python_manifest
from app.tools.repository import inspect_repository
from app.tools.upgrade import stage_python_upgrade
from app.tools.validation import CommandExecutor, validate_upgrade
from app.tools.worktree import DisposableWorktree, tracked_worktree_fingerprint, verify_staged_scope

APPROVAL_ID = "apply-upgrade"


class ApprovalGateError(ValueError):
    """Raised when a decision does not match the persisted approval gate."""


class CandidateSelector(Protocol):
    def select(
        self,
        repository: str,
        manifest: PythonManifest,
        advisory_provider: object,
    ) -> CandidateSelection: ...


class AdvisoryProvider(Protocol):
    def advisories_for(self, package: str, version: str) -> list[AdvisoryEvidence]: ...


class ReleaseProvider(Protocol):
    def release_for(self, package: str, version: str) -> ReleaseEvidence: ...


class FixtureCandidateSelector:
    """Deterministic selector for the reproducible no-credentials demonstration."""

    def select(
        self,
        repository: str,
        manifest: PythonManifest,
        advisory_provider: object,
    ) -> CandidateSelection:
        del repository

        @tool
        def fixture_candidate(payload: dict) -> dict:
            """Read locked dependencies and fixture advisories to select a supported upgrade."""
            return _fixture_candidate(
                PythonManifest.model_validate(payload), advisory_provider
            ).model_dump(mode="json")

        return fixture_advice(
            manifest.model_dump(mode="json"), fixture_candidate, CandidateSelection
        )


def _fixture_candidate(manifest: PythonManifest, advisory_provider: object) -> CandidateSelection:
    provider = advisory_provider
    if not hasattr(provider, "advisories_for"):
        raise ValueError("advisory provider does not implement advisories_for")
    for dependency in manifest.dependencies:
        if dependency.resolved_version is None:
            continue
        advisories = provider.advisories_for(dependency.name, dependency.resolved_version)
        for advisory in advisories:
            fixes = [
                v
                for v in advisory.fixed_versions
                if Version(v) > Version(dependency.resolved_version)
            ]
            if fixes:
                return CandidateSelection(
                    package=dependency.name,
                    current_version=dependency.resolved_version,
                    target_version=min(fixes, key=Version),
                    advisory_identifier=advisory.identifier,
                    rationale=(
                        f"{advisory.identifier} affects {dependency.name} "
                        f"{dependency.resolved_version} and is fixed in "
                        f"{min(fixes, key=Version)}."
                    ),
                )
    raise ValueError("no evidence-backed dependency upgrade is available")


class DependencyUpgradeWorkflow:
    def __init__(
        self,
        *,
        store: SQLiteStore,
        allowed_repository_root: Path,
        workspace_root: Path,
        selector: CandidateSelector,
        advisory_provider: AdvisoryProvider,
        release_provider: ReleaseProvider,
        command_runner: CommandExecutor,
        resolve_lock: bool = False,
        model_mode: str | None = None,
        evidence_mode: str | None = None,
    ) -> None:
        self.store = store
        self.allowed_repository_root = Path(allowed_repository_root).resolve(strict=True)
        self.workspace_root = Path(workspace_root)
        self.selector = selector
        self.advisory_provider = advisory_provider
        self.release_provider = release_provider
        self.command_runner = command_runner
        self.resolve_lock = resolve_lock
        self.model_mode = model_mode
        self.evidence_mode = evidence_mode
        self._decision_lock = RLock()

    def _event(
        self,
        run_id: str,
        *,
        kind: str,
        summary: str,
        payload: dict,
    ) -> None:
        self.store.append_event(
            run_id,
            kind=kind,
            summary=summary,
            payload=payload,
            idempotency_key=f"{run_id}:{kind}",
        )

    def start(self, repository: Path, *, run_id: str | None = None) -> WorkflowOutcome:
        run = self.store.create_run(
            "dependency_upgrade",
            str(repository),
            run_id=run_id,
        )
        run = self.store.transition_run(run.id, RunStatus.RUNNING)

        snapshot = inspect_repository(repository, allowed_root=self.allowed_repository_root)
        if snapshot.dirty:
            raise ValueError(
                "Repository has uncommitted changes. Commit or stash them, then start a new review."
            )
        self._event(
            run.id,
            kind="repository_inspected",
            summary=f"Inspected {snapshot.path.name} at {snapshot.head[:8]}",
            payload={
                **snapshot.model_dump(mode="json"),
                "provenance_version": 1,
                "source_mode": "captured_git_commit",
                "execution": {
                    "model_mode": self.model_mode,
                    "evidence_mode": self.evidence_mode,
                    "lock_resolution": self.resolve_lock,
                },
            },
        )
        manifest = scan_python_manifest(snapshot.path, revision=snapshot.head)
        self._event(
            run.id,
            kind="manifest_scanned",
            summary=f"Found {len(manifest.dependencies)} locked dependencies",
            payload={**manifest.model_dump(mode="json"), "source_revision": snapshot.head},
        )
        candidate = self.selector.select(
            str(snapshot.path),
            manifest,
            self.advisory_provider,
        )
        self._event(
            run.id,
            kind="candidate_selected",
            summary=(
                f"Selected {candidate.package} {candidate.current_version} → "
                f"{candidate.target_version}"
            ),
            payload={**candidate.model_dump(mode="json"), "source_revision": snapshot.head},
        )

        advisories = self.advisory_provider.advisories_for(
            candidate.package, candidate.current_version
        )
        if not any(
            dependency.name == candidate.package
            and dependency.resolved_version == candidate.current_version
            for dependency in manifest.dependencies
        ):
            raise ValueError("Selected dependency is not in the locked manifest")
        supporting = [
            item
            for item in advisories
            if item.identifier == candidate.advisory_identifier
            and item.package == candidate.package
            and item.affected_version == candidate.current_version
            and candidate.target_version in item.fixed_versions
        ]
        if not supporting or Version(candidate.target_version) <= Version(
            candidate.current_version
        ):
            raise ValueError("Selected upgrade is not supported by its advisory")
        release = self.release_provider.release_for(candidate.package, candidate.target_version)
        if release.package != candidate.package or release.version != candidate.target_version:
            raise ValueError("Release evidence does not match the selected upgrade")
        self._event(
            run.id,
            kind="evidence_collected",
            summary=f"Verified {candidate.advisory_identifier} and the fixed release",
            payload={
                "advisory_ids": [item.identifier for item in advisories],
                "advisories": [item.model_dump(mode="json") for item in advisories],
                "release": release.model_dump(mode="json"),
            },
        )

        with DisposableWorktree(
            snapshot.path, self.workspace_root, run_id=run.id, revision=snapshot.head
        ) as workspace:
            if scan_python_manifest(workspace) != manifest:
                raise ValueError("Staged manifest does not match the captured source revision")
            originals = {
                name: (workspace / name).read_text() for name in ("pyproject.toml", "uv.lock")
            }
            change = stage_python_upgrade(
                workspace,
                package=candidate.package,
                target_version=candidate.target_version,
            )
            if self.resolve_lock:
                # Resolve against the original lock, not the fixture's textual version rewrite.
                (workspace / "uv.lock").write_text(originals["uv.lock"])
                result = self.command_runner.execute(
                    CommandRequest(name=AllowedCommand.UV_LOCK, package=candidate.package),
                    cwd=workspace,
                )
                self._event(
                    run.id,
                    kind="lock_resolution_completed",
                    summary="Recorded lockfile resolution command",
                    payload={
                        "source_revision": snapshot.head,
                        "result": result.model_dump(mode="json"),
                    },
                )
                if result.exit_code != 0 or result.timed_out:
                    self.store.transition_run(run.id, RunStatus.FAILED)
                    raise ValueError("Lockfile resolution failed: " + result.stderr[-1000:])
                resolved = scan_python_manifest(workspace)
                if not any(
                    d.name == candidate.package and d.resolved_version == candidate.target_version
                    for d in resolved.dependencies
                ):
                    self.store.transition_run(run.id, RunStatus.FAILED)
                    raise ValueError("Resolved lock does not contain the selected version")
                change = change.model_copy(
                    update={
                        "diff": "".join(
                            "".join(
                                difflib.unified_diff(
                                    originals[name].splitlines(keepends=True),
                                    (workspace / name).read_text().splitlines(keepends=True),
                                    fromfile="a/" + name,
                                    tofile="b/" + name,
                                )
                            )
                            for name in originals
                        )
                    }
                )
            self._event(
                run.id,
                kind="upgrade_staged",
                summary="Staged the candidate in a disposable worktree",
                payload={**change.model_dump(mode="json"), "source_revision": snapshot.head},
            )
            verify_staged_scope(
                workspace, revision=snapshot.head, changed_files=change.changed_files
            )
            staged_tree = tracked_worktree_fingerprint(workspace)
            validation = validate_upgrade(
                workspace, runner=self.command_runner, resolved_environment=self.resolve_lock
            )
            unchanged_patch = tracked_worktree_fingerprint(workspace) == staged_tree
            if not unchanged_patch:
                validation = validation.model_copy(update={"passed": False})
            self._event(
                run.id,
                kind="validation_completed",
                summary="Validation passed" if validation.passed else "Validation failed",
                payload={
                    **validation.model_dump(mode="json"),
                    "source_revision": snapshot.head,
                    "patch_sha256": sha256(change.diff.encode()).hexdigest(),
                    "staged_files_unchanged": unchanged_patch,
                    "tracked_worktree_sha256": staged_tree,
                },
            )

        if not validation.passed:
            run = self.store.transition_run(run.id, RunStatus.FAILED)
            return WorkflowOutcome(run=run, candidate=candidate)

        material = review_material(run.id, self.store.list_events(run.id))
        self._event(
            run.id,
            kind="approval_required",
            summary="Human approval is required before accepting the validated patch",
            payload={
                "approval_id": APPROVAL_ID,
                "package": candidate.package,
                "from_version": candidate.current_version,
                "to_version": candidate.target_version,
                "provenance_version": 1,
                "review_sha256": review_digest(material),
            },
        )
        run = self.store.transition_run(run.id, RunStatus.WAITING_FOR_APPROVAL)
        return WorkflowOutcome(run=run, candidate=candidate, approval_id=APPROVAL_ID)

    def decide(
        self,
        run_id: str,
        *,
        approval_id: str,
        choice: ApprovalChoice,
    ) -> AgentRun:
        with self._decision_lock:
            return self._decide(run_id, approval_id=approval_id, choice=choice)

    def _decide(self, run_id: str, *, approval_id: str, choice: ApprovalChoice) -> AgentRun:
        if approval_id != APPROVAL_ID:
            raise ApprovalGateError("approval id does not match the active gate")
        try:
            return self.store.complete_approval(run_id, approval_id=approval_id, choice=choice)
        except ApprovalConflict as error:
            raise ApprovalGateError(str(error)) from error
