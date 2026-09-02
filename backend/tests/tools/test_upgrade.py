from pathlib import Path

import pytest

from app.domain.models import CommandResult
from app.tools.command_runner import AllowedCommand, CommandRequest
from app.tools.upgrade import UpgradeError, stage_python_upgrade
from app.tools.validation import validate_upgrade


def write_manifest(workspace: Path) -> None:
    (workspace / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\ndependencies = [\n  "jinja2==3.1.4",\n]\n'
    )
    (workspace / "uv.lock").write_text(
        'version = 1\n\n[[package]]\nname = "jinja2"\nversion = "3.1.4"\n'
    )


def test_stage_python_upgrade_changes_manifest_and_lockfile(tmp_path: Path) -> None:
    write_manifest(tmp_path)

    change = stage_python_upgrade(tmp_path, package="jinja2", target_version="3.1.5")

    assert change.from_version == "3.1.4"
    assert change.to_version == "3.1.5"
    assert change.changed_files == [Path("pyproject.toml"), Path("uv.lock")]
    assert '"jinja2==3.1.5"' in (tmp_path / "pyproject.toml").read_text()
    assert 'version = "3.1.5"' in (tmp_path / "uv.lock").read_text()
    assert "-  \"jinja2==3.1.4\"" in change.diff
    assert "+  \"jinja2==3.1.5\"" in change.diff


def test_stage_python_upgrade_rejects_unknown_package(tmp_path: Path) -> None:
    write_manifest(tmp_path)

    with pytest.raises(UpgradeError, match="not declared"):
        stage_python_upgrade(tmp_path, package="requests", target_version="2.32.5")


def test_stage_python_upgrade_rejects_unsafe_identifiers(tmp_path: Path) -> None:
    write_manifest(tmp_path)

    with pytest.raises(UpgradeError, match="package"):
        stage_python_upgrade(tmp_path, package="jinja2;echo bad", target_version="3.1.5")
    with pytest.raises(UpgradeError, match="version"):
        stage_python_upgrade(tmp_path, package="jinja2", target_version="3.1.5;echo bad")


class StubRunner:
    def __init__(self, result: CommandResult) -> None:
        self.result = result
        self.requests: list[tuple[CommandRequest, Path]] = []

    def execute(self, request: CommandRequest, *, cwd: Path) -> CommandResult:
        self.requests.append((request, cwd))
        return self.result


def test_validation_uses_registered_pytest_command(tmp_path: Path) -> None:
    result = CommandResult(
        command=["python", "-m", "pytest", "-q"],
        exit_code=0,
        stdout="3 passed",
        stderr="",
        duration_seconds=0.2,
    )
    runner = StubRunner(result)

    report = validate_upgrade(tmp_path, runner=runner)

    assert report.passed is True
    assert runner.requests == [(CommandRequest(name=AllowedCommand.PYTEST), tmp_path)]


def test_validation_failure_is_preserved(tmp_path: Path) -> None:
    result = CommandResult(
        command=["python", "-m", "pytest", "-q"],
        exit_code=1,
        stdout="1 failed",
        stderr="",
        duration_seconds=0.2,
    )

    report = validate_upgrade(tmp_path, runner=StubRunner(result))

    assert report.passed is False
    assert report.results[0].stdout == "1 failed"
