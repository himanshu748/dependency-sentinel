import subprocess
from pathlib import Path

import pytest

from app.tools.command_runner import (
    AllowedCommand,
    CommandPolicyError,
    CommandRequest,
    CommandRunner,
)


def test_command_runner_builds_only_registered_pytest_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, "2 passed\n", "")

    monkeypatch.setattr("app.tools.command_runner.subprocess.run", fake_run)
    runner = CommandRunner(allowed_root=tmp_path)

    result = runner.execute(CommandRequest(name=AllowedCommand.PYTEST), cwd=tmp_path)

    assert result.exit_code == 0
    assert result.command[-4:] == ["-m", "pytest", "-q", "--disable-warnings"]
    assert captured["kwargs"]["shell"] is False  # type: ignore[index]


def test_command_runner_rejects_unregistered_or_malformed_requests(tmp_path: Path) -> None:
    runner = CommandRunner(allowed_root=tmp_path)

    with pytest.raises(ValueError):
        CommandRequest(name="curl")
    with pytest.raises(CommandPolicyError, match="package"):
        runner.execute(
            CommandRequest(name=AllowedCommand.UV_LOCK, package="jinja2; rm -rf /"),
            cwd=tmp_path,
        )


def test_command_runner_rejects_cwd_outside_boundary(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()

    runner = CommandRunner(allowed_root=allowed)

    with pytest.raises(CommandPolicyError, match="outside"):
        runner.execute(CommandRequest(name=AllowedCommand.PYTEST), cwd=outside)


def test_command_runner_redacts_secrets_from_captured_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            1,
            "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY=not-a-real-secret",
        )

    monkeypatch.setattr("app.tools.command_runner.subprocess.run", fake_run)

    result = CommandRunner(allowed_root=tmp_path).execute(
        CommandRequest(name=AllowedCommand.PYTEST), cwd=tmp_path
    )

    assert "AKIAIOSFODNN7EXAMPLE" not in result.stdout
    assert "not-a-real-secret" not in result.stderr
    assert "[REDACTED]" in result.stdout
    assert "[REDACTED]" in result.stderr


def test_command_runner_reports_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, 2, output="partial", stderr="slow")

    monkeypatch.setattr("app.tools.command_runner.subprocess.run", fake_run)

    result = CommandRunner(allowed_root=tmp_path, timeout_seconds=2).execute(
        CommandRequest(name=AllowedCommand.PYTEST), cwd=tmp_path
    )

    assert result.exit_code == 124
    assert result.timed_out is True
    assert result.stdout == "partial"
