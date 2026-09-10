"""Exercise package resolution and functional validation without a model call."""

import os
import shutil
from pathlib import Path

import pytest

from app.tools.command_runner import AllowedCommand, CommandRequest, CommandRunner
from app.tools.upgrade import stage_python_upgrade
from app.tools.validation import validate_upgrade


@pytest.mark.skipif(
    os.getenv("SENTINEL_RUN_PACKAGE_INTEGRATION") != "1",
    reason="Opt-in package index access; no model or AWS calls",
)
def test_resolved_owned_fixture(tmp_path):
    root = Path(__file__).resolve().parents[2]
    source = tmp_path / "fixture"
    shutil.copytree(root / "fixtures/vulnerable-python-project", source)
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copyfile(root / "fixtures/live-validation" / name, source / name)
    shutil.copyfile(
        root / "fixtures/live-validation/test_installed_package.py",
        source / "tests/test_validated_version.py",
    )
    stage_python_upgrade(source, package="jinja2", target_version="3.1.5")
    runner = CommandRunner(allowed_root=tmp_path)
    resolved = runner.execute(
        CommandRequest(name=AllowedCommand.UV_LOCK, package="jinja2"), cwd=source
    )
    assert resolved.exit_code == 0, resolved.stderr
    report = validate_upgrade(source, runner=runner, resolved_environment=True)
    assert report.passed, report.results[0].stdout + report.results[0].stderr
