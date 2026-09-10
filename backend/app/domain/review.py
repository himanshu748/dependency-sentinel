"""Consistency checks for saved review records; these are not signed attestations."""

import json
import math
import re
from hashlib import sha256

from packaging.version import Version
from pydantic import ValidationError

from app.domain.models import (
    AdvisoryEvidence,
    AgentRun,
    ApprovalChoice,
    ApprovalDecision,
    CandidateSelection,
    CommandResult,
    PythonManifest,
    ReleaseEvidence,
    RunEvent,
    RunStatus,
    ValidationReport,
)

MATERIAL_KINDS = (
    "repository_inspected",
    "manifest_scanned",
    "candidate_selected",
    "evidence_collected",
    "upgrade_staged",
    "validation_completed",
)


class ReviewExportError(ValueError):
    """A saved run cannot support an approved export."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewExportError(message + " Start a new review to create an exportable record.")


def _one(events: list[RunEvent], kind: str) -> RunEvent:
    matches = [event for event in events if event.kind == kind]
    _require(len(matches) == 1, f"Saved review is missing or has duplicate {kind} evidence.")
    return matches[0]


def review_digest(material: dict) -> str:
    return sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def review_material(run_id: str, events: list[RunEvent]) -> dict:
    selected = [_one(events, kind) for kind in MATERIAL_KINDS]
    _require(
        all(event.run_id == run_id for event in selected), "Saved events belong to another run."
    )
    _require(
        [event.sequence for event in selected] == sorted({event.sequence for event in selected}),
        "Saved review steps are out of order.",
    )
    snapshot, manifest, candidate, evidence, change, validation = [e.payload for e in selected]
    resolution = [event for event in events if event.kind == "lock_resolution_completed"]
    execution = snapshot.get("execution")
    _require(isinstance(execution, dict), "Saved execution mode metadata is missing.")
    if execution.get("lock_resolution"):
        resolution_event = _one(events, "lock_resolution_completed")
        selected.insert(4, resolution_event)
        try:
            result = CommandResult.model_validate(resolution_event.payload["result"], strict=True)
        except (ValidationError, KeyError, TypeError) as error:
            raise ReviewExportError("Saved lockfile resolution result is invalid.") from error
        _require(
            resolution_event.payload.get("source_revision") == snapshot.get("head")
            and result.exit_code == 0
            and not result.timed_out
            and bool(result.command)
            and selected[3].sequence < resolution_event.sequence < selected[5].sequence,
            "Saved lockfile resolution did not complete at the captured revision.",
        )
    else:
        _require(not resolution, "Saved execution mode does not match lockfile resolution.")
    revision = snapshot.get("head")
    _require(
        snapshot.get("provenance_version") == 1
        and snapshot.get("source_mode") == "captured_git_commit"
        and isinstance(revision, str)
        and bool(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision))
        and snapshot.get("dirty") is False,
        "This saved run lacks verified source provenance.",
    )
    _require(
        all(
            item.get("source_revision") == revision
            for item in (manifest, candidate, change, validation)
        ),
        "Saved selection, patch and validation do not match the captured source revision.",
    )
    tracked_fingerprint = validation.get("tracked_worktree_sha256")
    _require(
        isinstance(tracked_fingerprint, str)
        and bool(re.fullmatch(r"[0-9a-fA-F]{64}", tracked_fingerprint)),
        "Saved review lacks a valid tracked-worktree fingerprint.",
    )
    try:
        parsed_manifest = PythonManifest.model_validate(manifest)
        selection = CandidateSelection.model_validate(candidate)
        increasing_version = Version(selection.target_version) > Version(selection.current_version)
        report = ValidationReport.model_validate(validation, strict=True)
        advisories = [AdvisoryEvidence.model_validate(item) for item in evidence["advisories"]]
        release = ReleaseEvidence.model_validate(evidence["release"])
    except (ValueError, KeyError, TypeError) as error:
        raise ReviewExportError(
            "Saved review evidence is incomplete or invalid. Start a new review."
        ) from error
    _require(
        report.passed
        and validation.get("staged_files_unchanged") is True
        and bool(report.results)
        and all(
            item.exit_code == 0
            and not item.timed_out
            and bool(item.command)
            and all(part.strip() for part in item.command)
            and item.duration_seconds >= 0
            and math.isfinite(item.duration_seconds)
            for item in report.results
        )
        and all("timed_out" in item for item in validation["results"])
        and any("pytest" in item.command for item in report.results),
        "Saved review does not contain successful, complete test results.",
    )
    _require(
        any(
            item.name == selection.package and item.resolved_version == selection.current_version
            for item in parsed_manifest.dependencies
        )
        and change.get("package") == selection.package
        and change.get("from_version") == selection.current_version
        and change.get("to_version") == selection.target_version
        and increasing_version,
        "Saved candidate does not match the manifest and patch.",
    )
    _require(
        any(
            item.identifier == selection.advisory_identifier
            and item.package == selection.package
            and item.affected_version == selection.current_version
            and selection.target_version in item.fixed_versions
            for item in advisories
        )
        and release.package == selection.package
        and release.version == selection.target_version,
        "Saved advisory and release evidence do not support the selected candidate.",
    )
    patch = change.get("diff")
    _require(isinstance(patch, str) and bool(patch.strip()), "Saved patch is empty.")
    _require(
        validation.get("patch_sha256") == sha256(patch.encode()).hexdigest(),
        "Saved patch does not match the validated patch digest.",
    )
    changed_files = change.get("changed_files")
    _require(
        isinstance(changed_files, list)
        and all(isinstance(name, str) for name in changed_files)
        and set(changed_files) == {"pyproject.toml", "uv.lock"},
        "Saved patch file list is incomplete or unsupported.",
    )
    return {
        "schema_version": 1,
        "run_id": run_id,
        "events": [event.model_dump(mode="json") for event in selected],
    }


def validate_gate(run_id: str, events: list[RunEvent]) -> tuple[dict, RunEvent, str]:
    material = review_material(run_id, events)
    gate = _one(events, "approval_required")
    digest = review_digest(material)
    _require(
        gate.payload.get("provenance_version") == 1
        and gate.payload.get("review_sha256") == digest
        and gate.sequence > _one(events, "validation_completed").sequence,
        "Saved review has changed since its approval gate was created.",
    )
    selection = _one(events, "candidate_selected").payload
    _require(
        gate.payload.get("package") == selection["package"]
        and gate.payload.get("from_version") == selection["current_version"]
        and gate.payload.get("to_version") == selection["target_version"],
        "Saved approval gate does not match the candidate.",
    )
    return material, gate, digest


def approved_review(
    run: AgentRun, events: list[RunEvent], decision: ApprovalDecision | None
) -> tuple[dict, str]:
    _require(run.status is RunStatus.COMPLETED, "Only completed approved reviews can be exported.")
    material, gate, digest = validate_gate(run.id, events)
    _require(
        decision is not None
        and decision.run_id == run.id
        and decision.choice is ApprovalChoice.APPROVED
        and decision.approval_id == gate.payload.get("approval_id"),
        "This run has no matching human approval.",
    )
    recorded = _one(events, "approval_recorded")
    completed = _one(events, "report_completed")
    _require(
        recorded.payload.get("review_sha256") == digest
        and completed.payload.get("review_sha256") == digest
        and recorded.payload.get("choice") == "approved"
        and recorded.payload.get("approval_id") == decision.approval_id
        and completed.payload.get("approval_id") == decision.approval_id
        and recorded.payload.get("approved_at") == decision.created_at.isoformat()
        and completed.payload.get("source_checkout_modified") is False
        and gate.sequence < recorded.sequence < completed.sequence
        and decision.created_at >= gate.created_at,
        "Saved approval receipt does not match the reviewed record.",
    )
    by_kind = {event["kind"]: event["payload"] for event in material["events"]}
    change = by_kind["upgrade_staged"]
    receipt = {
        "schema_version": 1,
        "artifact": "dependency-sentinel-approved-review",
        "run": run.model_dump(mode="json"),
        "source": by_kind["repository_inspected"],
        "candidate": by_kind["candidate_selected"],
        "evidence": by_kind["evidence_collected"],
        "validation": by_kind["validation_completed"],
        "commands": (
            [by_kind["lock_resolution_completed"]["result"]]
            if "lock_resolution_completed" in by_kind
            else []
        )
        + by_kind["validation_completed"]["results"],
        "approval": decision.model_dump(mode="json"),
        "patch": {
            "sha256": sha256(change["diff"].encode()).hexdigest(),
            "changed_files": change["changed_files"],
            "encoding": "utf-8",
        },
        "review_sha256": digest,
        "review_material": material,
        "source_checkout_modified": False,
        "integrity_scope": "Consistency of the local saved record; not a signed attestation.",
    }
    return receipt, change["diff"]
