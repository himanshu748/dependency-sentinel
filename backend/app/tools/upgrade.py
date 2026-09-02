import difflib
import re
from pathlib import Path

from app.domain.models import UpgradeChange


class UpgradeError(ValueError):
    """Raised when an upgrade cannot be staged without ambiguity."""


_PACKAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_VERSION = re.compile(r"^[0-9][A-Za-z0-9.!+_-]*$")


def _replace_declared_dependency(text: str, package: str, target_version: str) -> str:
    pattern = re.compile(
        rf'(?P<quote>["\']){re.escape(package)}(?P<constraint>[^"\']*)(?P=quote)',
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if match is None:
        raise UpgradeError(f"package {package!r} is not declared")
    replacement = f'{match.group("quote")}{package}=={target_version}{match.group("quote")}'
    return f"{text[: match.start()]}{replacement}{text[match.end() :]}"


def _replace_locked_version(text: str, package: str, target_version: str) -> tuple[str, str]:
    pattern = re.compile(
        rf'(\[\[package\]\]\s+name\s*=\s*"{re.escape(package)}"\s+'
        rf'version\s*=\s*")(?P<version>[^"]+)(")',
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if match is None:
        raise UpgradeError(f"package {package!r} is not present in uv.lock")
    previous = match.group("version")
    updated = f"{text[: match.start('version')]}{target_version}{text[match.end('version') :]}"
    return updated, previous


def _diff(path: Path, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def stage_python_upgrade(workspace: Path, *, package: str, target_version: str) -> UpgradeChange:
    if not _PACKAGE.fullmatch(package):
        raise UpgradeError("package contains unsupported characters")
    if not _VERSION.fullmatch(target_version):
        raise UpgradeError("version contains unsupported characters")

    root = Path(workspace).resolve(strict=True)
    manifest_path = root / "pyproject.toml"
    lock_path = root / "uv.lock"
    before_manifest = manifest_path.read_text()
    before_lock = lock_path.read_text()

    after_manifest = _replace_declared_dependency(before_manifest, package, target_version)
    after_lock, previous_version = _replace_locked_version(before_lock, package, target_version)
    if previous_version == target_version:
        raise UpgradeError("target version is already locked")

    manifest_path.write_text(after_manifest)
    lock_path.write_text(after_lock)
    diff = _diff(Path("pyproject.toml"), before_manifest, after_manifest)
    diff += _diff(Path("uv.lock"), before_lock, after_lock)
    return UpgradeChange(
        package=package,
        from_version=previous_version,
        to_version=target_version,
        changed_files=[Path("pyproject.toml"), Path("uv.lock")],
        diff=diff,
    )
