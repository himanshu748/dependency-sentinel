from pathlib import Path
from typing import Protocol

from strands import tool

from app.domain.models import AdvisoryEvidence, ReleaseEvidence
from app.tools.python_manifest import scan_python_manifest as scan_manifest
from app.tools.repository import inspect_repository as inspect


class AdvisoryProvider(Protocol):
    def advisories_for(self, package: str, version: str) -> list[AdvisoryEvidence]: ...


class ReleaseProvider(Protocol):
    def release_for(self, package: str, version: str) -> ReleaseEvidence: ...


def build_read_only_tools(
    *,
    allowed_repository_root: Path,
    advisory_provider: AdvisoryProvider,
    release_provider: ReleaseProvider,
) -> list[object]:
    root = Path(allowed_repository_root).resolve(strict=True)

    @tool(name="inspect_repository")
    def inspect_repository(repository: str) -> dict:
        """Inspect Git identity and cleanliness without modifying the repository.

        Args:
            repository: Absolute path to a repository under the configured root.
        """
        return inspect(Path(repository), allowed_root=root).model_dump(mode="json")

    @tool(name="scan_python_manifest")
    def scan_python_manifest(repository: str) -> dict:
        """Read Python dependency declarations and locked versions.

        Args:
            repository: Absolute path to the validated repository root.
        """
        snapshot = inspect(Path(repository), allowed_root=root)
        return scan_manifest(snapshot.path).model_dump(mode="json")

    @tool(name="lookup_advisories")
    def lookup_advisories(package: str, version: str) -> list[dict]:
        """Look up official vulnerability evidence for a locked package version.

        Args:
            package: Normalized Python package name.
            version: Locked package version.
        """
        return [
            advisory.model_dump(mode="json")
            for advisory in advisory_provider.advisories_for(package, version)
        ]

    @tool(name="lookup_release")
    def lookup_release(package: str, version: str) -> dict:
        """Look up official release evidence for a proposed fixed version.

        Args:
            package: Normalized Python package name.
            version: Proposed fixed package version.
        """
        return release_provider.release_for(package, version).model_dump(mode="json")

    return [inspect_repository, scan_python_manifest, lookup_advisories, lookup_release]
