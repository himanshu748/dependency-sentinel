from pathlib import Path

import pytest

from app.agent.orchestrator import ApprovalGateError
from app.domain.models import ApprovalChoice, RunStatus

from .test_upgrade_workflow import PassingRunner, seeded_repository, workflow


def test_approved_run_resumes_and_completes(tmp_path: Path) -> None:
    repository = seeded_repository(tmp_path)
    service, store = workflow(tmp_path, runner=PassingRunner())
    paused = service.start(repository, run_id="run-approved")

    completed = service.decide(
        paused.run.id,
        approval_id="apply-upgrade",
        choice=ApprovalChoice.APPROVED,
    )

    assert completed.status is RunStatus.COMPLETED
    assert store.has_approval(paused.run.id, "apply-upgrade") is True
    assert [event.kind for event in store.list_events(paused.run.id)][-2:] == [
        "approval_recorded",
        "report_completed",
    ]


def test_rejected_run_is_cancelled_without_post_approval_action(tmp_path: Path) -> None:
    repository = seeded_repository(tmp_path)
    service, store = workflow(tmp_path, runner=PassingRunner())
    paused = service.start(repository, run_id="run-rejected")

    cancelled = service.decide(
        paused.run.id,
        approval_id="apply-upgrade",
        choice=ApprovalChoice.REJECTED,
    )

    assert cancelled.status is RunStatus.CANCELLED
    kinds = [event.kind for event in store.list_events(paused.run.id)]
    assert kinds[-1] == "approval_rejected"
    assert "report_completed" not in kinds


def test_approval_id_and_paused_state_are_enforced(tmp_path: Path) -> None:
    repository = seeded_repository(tmp_path)
    service, _ = workflow(tmp_path, runner=PassingRunner())
    paused = service.start(repository, run_id="run-gated")

    with pytest.raises(ApprovalGateError, match="approval id"):
        service.decide(
            paused.run.id,
            approval_id="skip-gate",
            choice=ApprovalChoice.APPROVED,
        )

    service.decide(
        paused.run.id,
        approval_id="apply-upgrade",
        choice=ApprovalChoice.REJECTED,
    )
    with pytest.raises(ApprovalGateError, match="not waiting"):
        service.decide(
            paused.run.id,
            approval_id="apply-upgrade",
            choice=ApprovalChoice.REJECTED,
        )
