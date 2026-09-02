from pathlib import Path

import pytest


def test_manifest_scanner_pairs_declared_requirements_with_locked_versions() -> None:
    """Catch an upgrade decision made without the repository's resolved versions."""
    try:
        from app.tools.python_manifest import scan_python_manifest
    except ImportError:
        pytest.fail("Python manifest scanner is not implemented")

    repository = Path(__file__).parents[3] / "fixtures" / "vulnerable-python-project"

    result = scan_python_manifest(repository)

    assert result.project_name == "sentinel-fixture"
    assert [dependency.name for dependency in result.dependencies] == ["click", "jinja2"]
    assert result.dependencies[0].declared_requirement == "click>=8.1,<9"
    assert result.dependencies[0].resolved_version == "8.1.8"
    assert result.dependencies[1].declared_requirement == "jinja2==3.1.4"
    assert result.dependencies[1].resolved_version == "3.1.4"
    assert all(dependency.ecosystem == "pypi" for dependency in result.dependencies)


def test_manifest_scanner_rejects_missing_project_metadata(tmp_path: Path) -> None:
    """Catch a misleading empty scan when no Python project exists."""
    try:
        from app.tools.python_manifest import ManifestError, scan_python_manifest
    except ImportError:
        pytest.fail("Python manifest scanner is not implemented")

    with pytest.raises(ManifestError, match="pyproject.toml"):
        scan_python_manifest(tmp_path)

