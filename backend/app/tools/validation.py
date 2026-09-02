from pathlib import Path
from typing import Protocol

from app.domain.models import CommandResult, ValidationReport
from app.tools.command_runner import AllowedCommand, CommandRequest


class CommandExecutor(Protocol):
    def execute(self, request: CommandRequest, *, cwd: Path) -> CommandResult: ...


def validate_upgrade(workspace: Path, *, runner: CommandExecutor) -> ValidationReport:
    result = runner.execute(CommandRequest(name=AllowedCommand.PYTEST), cwd=workspace)
    return ValidationReport(passed=result.exit_code == 0 and not result.timed_out, results=[result])
