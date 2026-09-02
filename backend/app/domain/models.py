from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalChoice(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


def utc_now() -> datetime:
    return datetime.now(UTC)


class AgentRun(BaseModel):
    id: str
    task_type: str
    input_summary: str
    status: RunStatus = RunStatus.QUEUED
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RunEvent(BaseModel):
    id: str
    run_id: str
    sequence: int
    kind: str
    summary: str
    payload: dict[str, Any]
    idempotency_key: str
    created_at: datetime = Field(default_factory=utc_now)


class ApprovalDecision(BaseModel):
    id: str
    run_id: str
    approval_id: str
    choice: ApprovalChoice
    created_at: datetime = Field(default_factory=utc_now)


class RepositorySnapshot(BaseModel):
    path: Path
    head: str
    branch: str
    dirty: bool


class DependencyRecord(BaseModel):
    name: str
    ecosystem: str
    declared_requirement: str
    resolved_version: str | None


class PythonManifest(BaseModel):
    project_name: str
    requires_python: str | None
    dependencies: list[DependencyRecord]


class EvidenceSource(BaseModel):
    publisher: str
    url: str
    title: str
    excerpt: str
    retrieved_at: datetime


class AdvisoryEvidence(BaseModel):
    identifier: str
    package: str
    affected_version: str
    fixed_versions: list[str]
    summary: str
    severity: str | None = None
    source: EvidenceSource


class ReleaseEvidence(BaseModel):
    package: str
    version: str
    summary: str
    source: EvidenceSource


class CommandResult(BaseModel):
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False


class UpgradeChange(BaseModel):
    package: str
    from_version: str
    to_version: str
    changed_files: list[Path]
    diff: str


class ValidationReport(BaseModel):
    passed: bool
    results: list[CommandResult]


class CandidateSelection(BaseModel):
    package: str
    current_version: str
    target_version: str
    advisory_identifier: str
    rationale: str


class WorkflowOutcome(BaseModel):
    run: AgentRun
    candidate: CandidateSelection
    approval_id: str | None = None
