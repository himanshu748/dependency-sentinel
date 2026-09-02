import pytest


def _state_machine_api():
    try:
        from app.domain.models import RunStatus
        from app.domain.state_machine import InvalidStateTransition, transition_run
    except ImportError:
        pytest.fail("run state machine is not implemented")
    return RunStatus, InvalidStateTransition, transition_run


def test_waiting_run_resumes_only_after_an_approval_decision() -> None:
    """Catch a bypass that resumes a paused agent without recorded approval."""
    RunStatus, InvalidStateTransition, transition_run = _state_machine_api()

    with pytest.raises(InvalidStateTransition, match="approval decision"):
        transition_run(
            RunStatus.WAITING_FOR_APPROVAL,
            RunStatus.RUNNING,
            approval_recorded=False,
        )

    assert (
        transition_run(
            RunStatus.WAITING_FOR_APPROVAL,
            RunStatus.RUNNING,
            approval_recorded=True,
        )
        is RunStatus.RUNNING
    )


def test_completed_run_is_terminal() -> None:
    """Catch accidental mutation of a completed run back into active work."""
    RunStatus, InvalidStateTransition, transition_run = _state_machine_api()

    with pytest.raises(InvalidStateTransition, match="completed"):
        transition_run(RunStatus.COMPLETED, RunStatus.RUNNING)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("queued", "running"),
        ("queued", "cancelled"),
        ("running", "waiting_for_approval"),
        ("running", "completed"),
        ("running", "failed"),
        ("running", "cancelled"),
        ("waiting_for_approval", "cancelled"),
        ("waiting_for_approval", "failed"),
    ],
)
def test_expected_run_transitions_are_allowed(current: str, target: str) -> None:
    """Catch removal of a lifecycle transition required by the agent workflow."""
    RunStatus, _, transition_run = _state_machine_api()

    assert transition_run(RunStatus(current), RunStatus(target)) is RunStatus(target)
