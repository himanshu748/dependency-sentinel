from app.domain.models import RunStatus


class InvalidStateTransition(ValueError):
    """Raised when a run lifecycle change would violate the workflow contract."""


_ALLOWED_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.QUEUED: frozenset({RunStatus.RUNNING, RunStatus.CANCELLED}),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.WAITING_FOR_APPROVAL,
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        }
    ),
    RunStatus.WAITING_FOR_APPROVAL: frozenset(
        {RunStatus.RUNNING, RunStatus.FAILED, RunStatus.CANCELLED}
    ),
    RunStatus.COMPLETED: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.CANCELLED: frozenset(),
}


def transition_run(
    current: RunStatus,
    target: RunStatus,
    *,
    approval_recorded: bool = False,
) -> RunStatus:
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise InvalidStateTransition(f"cannot transition {current.value} to {target.value}")
    if (
        current is RunStatus.WAITING_FOR_APPROVAL
        and target is RunStatus.RUNNING
        and not approval_recorded
    ):
        raise InvalidStateTransition("an approval decision is required before resuming")
    return target
