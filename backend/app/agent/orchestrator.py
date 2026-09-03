from pathlib import Path
from typing import Protocol

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
from app.storage.sqlite import SQLiteStore
from app.tools.python_manifest import scan_python_manifest
from app.tools.repository import inspect_repository
from app.tools.upgrade import stage_python_upgrade
from app.tools.validation import CommandExecutor, validate_upgrade
from app.tools.worktree import DisposableWorktree

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
        provider = advisory_provider
        if not hasattr(provider, "advisories_for"):
            raise ValueError("advisory provider does not implement advisories_for")
        for dependency in manifest.dependencies:
            if dependency.resolved_version is None:
                continue
            advisories = provider.advisories_for(dependency.name, dependency.resolved_version)
            for advisory in advisories:
                if advisory.fixed_versions:
                    return CandidateSelection(
                        package=dependency.name,
                        current_version=dependency.resolved_version,
                        target_version=advisory.fixed_versions[0],
                        advisory_identifier=advisory.identifier,
                        rationale=(
                            f"{advisory.identifier} affects {dependency.name} "
                            f"{dependency.resolved_version} and is fixed in "
                            f"{advisory.fixed_versions[0]}."
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
    ) -> None:
        self.store = store
        self.allowed_repository_root = Path(allowed_repository_root).resolve(strict=True)
        self.workspace_root = Path(workspace_root)
        self.selector = selector
        self.advisory_provider = advisory_provider
        self.release_provider = release_provider
        self.command_runner = command_runner

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
        self._event(
            run.id,
            kind="repository_inspected",
            summary=f"Inspected {snapshot.path.name} at {snapshot.head[:8]}",
            payload=snapshot.model_dump(mode="json"),
        )
        manifest = scan_python_manifest(snapshot.path)
        self._event(
            run.id,
            kind="manifest_scanned",
            summary=f"Found {len(manifest.dependencies)} locked dependencies",
            payload=manifest.model_dump(mode="json"),
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
            payload=candidate.model_dump(mode="json"),
        )

        advisories = self.advisory_provider.advisories_for(
            candidate.package, candidate.current_version
        )
        release = self.release_provider.release_for(candidate.package, candidate.target_version)
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

        with DisposableWorktree(snapshot.path, self.workspace_root, run_id=run.id) as workspace:
            change = stage_python_upgrade(
                workspace,
                package=candidate.package,
                target_version=candidate.target_version,
            )
            self._event(
                run.id,
                kind="upgrade_staged",
                summary="Staged the candidate in a disposable worktree",
                payload=change.model_dump(mode="json"),
            )
            validation = validate_upgrade(workspace, runner=self.command_runner)
            self._event(
                run.id,
                kind="validation_completed",
                summary="Validation passed" if validation.passed else "Validation failed",
                payload=validation.model_dump(mode="json"),
            )

        if not validation.passed:
            run = self.store.transition_run(run.id, RunStatus.FAILED)
            return WorkflowOutcome(run=run, candidate=candidate)

        self._event(
            run.id,
            kind="approval_required",
            summary="Human approval is required before accepting the validated patch",
            payload={
                "approval_id": APPROVAL_ID,
                "package": candidate.package,
                "from_version": candidate.current_version,
                "to_version": candidate.target_version,
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
        run = self.store.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        if run.status is not RunStatus.WAITING_FOR_APPROVAL:
            raise ApprovalGateError("run is not waiting for approval")
        if approval_id != APPROVAL_ID:
            raise ApprovalGateError("approval id does not match the active gate")

        self.store.record_approval(
            run_id,
            approval_id=approval_id,
            choice=choice,
        )
        if choice is ApprovalChoice.REJECTED:
            self._event(
                run_id,
                kind="approval_rejected",
                summary="The validated patch was rejected and no action was taken",
                payload={"approval_id": approval_id, "choice": choice.value},
            )
            return self.store.transition_run(run_id, RunStatus.CANCELLED)

        run = self.store.transition_run(
            run_id,
            RunStatus.RUNNING,
            approval_recorded=self.store.has_approval(run_id, approval_id),
        )
        self._event(
            run_id,
            kind="approval_recorded",
            summary="The human approved the validated patch",
            payload={"approval_id": approval_id, "choice": choice.value},
        )
        self._event(
            run_id,
            kind="report_completed",
            summary="The approved evidence and validation report is complete",
            payload={"approval_id": approval_id, "source_checkout_modified": False},
        )
        return self.store.transition_run(run.id, RunStatus.COMPLETED)
