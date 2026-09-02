import re
import subprocess
import sys
import time
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

from app.domain.models import CommandResult


class CommandPolicyError(ValueError):
    """Raised when a requested command violates the fixed execution policy."""


class AllowedCommand(StrEnum):
    PYTEST = "pytest"
    UV_LOCK = "uv_lock"


class CommandRequest(BaseModel):
    name: AllowedCommand
    package: str | None = None


_PACKAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SECRET_PATTERNS = (
    re.compile(r"(?i)(AWS_ACCESS_KEY_ID\s*=\s*)\S+"),
    re.compile(r"(?i)(AWS_SECRET_ACCESS_KEY\s*=\s*)\S+"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\b(?:sk|ghp)_[A-Za-z0-9_-]{16,}\b"),
)


def _redact(value: str | bytes | None) -> str:
    if value is None:
        return ""
    text = value.decode(errors="replace") if isinstance(value, bytes) else value
    for pattern in _SECRET_PATTERNS:
        if pattern.groups:
            text = pattern.sub(r"\1[REDACTED]", text)
        else:
            text = pattern.sub("[REDACTED]", text)
    return text


class CommandRunner:
    def __init__(self, *, allowed_root: Path, timeout_seconds: int = 120) -> None:
        self.allowed_root = Path(allowed_root).resolve(strict=True)
        self.timeout_seconds = timeout_seconds

    def _build_command(self, request: CommandRequest) -> list[str]:
        if request.name is AllowedCommand.PYTEST:
            if request.package is not None:
                raise CommandPolicyError("pytest does not accept a package argument")
            return [sys.executable, "-m", "pytest", "-q", "--disable-warnings"]

        if request.name is AllowedCommand.UV_LOCK:
            if request.package is None or not _PACKAGE.fullmatch(request.package):
                raise CommandPolicyError("package contains unsupported characters")
            return ["uv", "lock", "--upgrade-package", request.package]

        raise CommandPolicyError("command is not registered")

    def execute(self, request: CommandRequest, *, cwd: Path) -> CommandResult:
        working_directory = Path(cwd).resolve(strict=True)
        try:
            working_directory.relative_to(self.allowed_root)
        except ValueError as error:
            raise CommandPolicyError("working directory is outside the allowed root") from error

        command = self._build_command(request)
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                cwd=working_directory,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
            )
            return CommandResult(
                command=command,
                exit_code=completed.returncode,
                stdout=_redact(completed.stdout),
                stderr=_redact(completed.stderr),
                duration_seconds=time.monotonic() - started,
            )
        except subprocess.TimeoutExpired as error:
            return CommandResult(
                command=command,
                exit_code=124,
                stdout=_redact(error.output),
                stderr=_redact(error.stderr),
                duration_seconds=time.monotonic() - started,
                timed_out=True,
            )
