import re
import subprocess
import tomllib
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement

from app.domain.models import DependencyRecord, PythonManifest


class ManifestError(ValueError):
    """Raised when Python project metadata cannot be scanned safely."""


def _load_toml(path: Path) -> dict:
    try:
        with path.open("rb") as source:
            return tomllib.load(source)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ManifestError(f"cannot read {path.name}: {error}") from error


def scan_python_manifest(repository: Path, *, revision: str | None = None) -> PythonManifest:
    repository = Path(repository)
    if revision is not None:
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision):
            raise ManifestError("manifest revision must be a full captured commit SHA")
        committed = {}
        for name in ("pyproject.toml", "uv.lock"):
            result = subprocess.run(
                ["git", "-C", str(repository), "show", f"{revision}:{name}"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise ManifestError(f"{name} must be tracked in the captured commit")
            try:
                committed[name] = tomllib.loads(result.stdout)
            except tomllib.TOMLDecodeError as error:
                raise ManifestError(f"cannot read committed {name}: {error}") from error
        return _scan_manifest(committed["pyproject.toml"], committed["uv.lock"])
    manifest_path = repository / "pyproject.toml"
    if not manifest_path.is_file():
        raise ManifestError("pyproject.toml is required")

    manifest = _load_toml(manifest_path)
    lock_path = repository / "uv.lock"
    lock = _load_toml(lock_path) if lock_path.is_file() else {}
    return _scan_manifest(manifest, lock)


def _scan_manifest(manifest: dict, lock: dict) -> PythonManifest:
    project = manifest.get("project")
    if not isinstance(project, dict) or not project.get("name"):
        raise ManifestError("pyproject.toml must define project.name")

    locked_versions: dict[str, str] = {}
    for package in lock.get("package", []):
        if isinstance(package, dict) and package.get("name") and package.get("version"):
            locked_versions[str(package["name"]).lower()] = str(package["version"])

    dependencies: list[DependencyRecord] = []
    for declared in project.get("dependencies", []):
        try:
            requirement = Requirement(str(declared))
        except InvalidRequirement as error:
            raise ManifestError(f"invalid dependency requirement: {declared}") from error
        dependencies.append(
            DependencyRecord(
                name=requirement.name.lower(),
                ecosystem="pypi",
                declared_requirement=str(declared),
                resolved_version=locked_versions.get(requirement.name.lower()),
            )
        )

    return PythonManifest(
        project_name=str(project["name"]),
        requires_python=project.get("requires-python"),
        dependencies=sorted(dependencies, key=lambda dependency: dependency.name),
    )
