"""Opt-in external-model workflow check on an owned temporary repository.

Direct mode uses recorded evidence. AgentCore mode queries OSV/PyPI and resolves
an isolated package environment before running the fixture's functional tests.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def git(repository, *arguments):
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-paid-requests", action="store_true")
    if not parser.parse_args().allow_paid_requests:
        parser.error("Real inference requires --allow-paid-requests")
    from app.agent.model import (
        AgentCoreCandidateSelector,
        StrandsCandidateSelector,
        create_strands_agent,
    )
    from app.agent.orchestrator import DependencyUpgradeWorkflow
    from app.agent.provider import (
        create_provider_model,
        validate_provider_configuration,
    )
    from app.agent.tools import build_read_only_tools
    from app.config import Settings
    from app.domain.models import ApprovalChoice, RunStatus
    from app.evidence.advisories import OsvAdvisoryProvider
    from app.evidence.fixtures import FixtureEvidenceStore
    from app.evidence.releases import PypiReleaseProvider
    from app.storage.sqlite import SQLiteStore
    from app.tools.command_runner import CommandRunner

    settings = Settings()
    validate_provider_configuration(settings)
    if settings.fixture_mode or settings.llm_provider != "openai-compatible":
        parser.error("Requires the external model, not fixture mode")
    with TemporaryDirectory(prefix="sentinel-live-smoke-") as temp:
        root = Path(temp)
        repository = root / "source"
        shutil.copytree(ROOT / "fixtures" / "vulnerable-python-project", repository)
        if settings.agentcore_runtime_arn:
            # A fresh owned fixture uses version-independent functional tests.
            # The historical fixed-version fixture remains unchanged in the repository.
            for name in ("pyproject.toml", "uv.lock"):
                shutil.copyfile(ROOT / "fixtures/live-validation" / name, repository / name)
            shutil.copyfile(
                ROOT / "fixtures/live-validation/test_installed_package.py",
                repository / "tests/test_validated_version.py",
            )
        git(repository, "init", "-q")
        git(repository, "config", "user.email", "sentinel@example.test")
        git(repository, "config", "user.name", "Dependency Sentinel")
        git(repository, "add", ".")
        git(repository, "commit", "-qm", "Owned verification fixture")
        original_head = git(repository, "rev-parse", "HEAD")
        workspaces = root / "workspaces"
        workspaces.mkdir()
        store = SQLiteStore(root / "runs.sqlite3")
        store.initialize()
        evidence = FixtureEvidenceStore(ROOT / "fixtures" / "evidence")
        releases = evidence
        if settings.agentcore_runtime_arn:
            evidence = OsvAdvisoryProvider()
            releases = PypiReleaseProvider()
            selector = AgentCoreCandidateSelector(
                settings.agentcore_runtime_arn, settings.aws_region
            )
        else:
            selector = StrandsCandidateSelector(
                create_strands_agent(
                    model_id=settings.selected_model_id,
                    region_name=settings.aws_region,
                    provider_model=create_provider_model(settings),
                    tools=build_read_only_tools(
                        allowed_repository_root=root,
                        advisory_provider=evidence,
                        release_provider=releases,
                    ),
                )
            )
        workflow = DependencyUpgradeWorkflow(
            store=store,
            allowed_repository_root=root,
            workspace_root=workspaces,
            selector=selector,
            advisory_provider=evidence,
            release_provider=releases,
            command_runner=CommandRunner(allowed_root=workspaces),
            resolve_lock=bool(settings.agentcore_runtime_arn),
            model_mode="agentcore" if settings.agentcore_runtime_arn else "openai-compatible",
            evidence_mode="live" if settings.agentcore_runtime_arn else "fixture",
        )
        result = workflow.start(repository, run_id="run-external-smoke")
        if result.run.status is not RunStatus.WAITING_FOR_APPROVAL:
            validations = [
                event
                for event in store.list_events(result.run.id)
                if event.kind == "validation_completed"
            ]
            diagnostics = []
            for event in validations:
                for command in event.payload.get("results", []):
                    for line in (
                        command.get("stdout", "") + command.get("stderr", "")
                    ).splitlines():
                        if line.startswith(("E ", "FAILED ", "ERROR ", "error:")):
                            diagnostics.append(
                                re.sub(r"\b(?:gsk|sk|ghp)_[A-Za-z0-9_-]+", "[REDACTED]", line[:300])
                            )
            print(
                json.dumps(
                    {
                        "workflow_status": result.run.status.value,
                        "target_version": result.candidate.target_version,
                        "validation_diagnostics": diagnostics[:10],
                        "event_kinds": [event.kind for event in store.list_events(result.run.id)],
                    }
                )
            )
        assert result.run.status is RunStatus.WAITING_FOR_APPROVAL
        assert result.candidate.package == "jinja2"
        if not settings.agentcore_runtime_arn:
            assert result.candidate.target_version == "3.1.5"
        validation = next(
            e for e in store.list_events(result.run.id) if e.kind == "validation_completed"
        )
        assert validation.payload["passed"] is True
        if settings.agentcore_runtime_arn:
            assert selector.runtime.last_evidence["engine"] == "strands-openai-compatible"
            names = selector.runtime.last_evidence["tool_calls"]
        else:
            names = [
                block["toolUse"]["name"]
                for message in selector.last_run_agent.messages
                for block in message.get("content", [])
                if "toolUse" in block
            ]
        assert "lookup_advisories" in names
        assert "lookup_release" in names
        approved = workflow.decide(
            result.run.id,
            approval_id=result.approval_id,
            choice=ApprovalChoice.APPROVED,
        )
        assert approved.status is RunStatus.COMPLETED
        assert git(repository, "rev-parse", "HEAD") == original_head
        assert git(repository, "status", "--porcelain=v1") == ""
        print(
            json.dumps(
                {
                    "service": "dependency-sentinel",
                    "model": settings.llm_model_id,
                    "runtime": "agentcore"
                    if settings.agentcore_runtime_arn
                    else "real-external-model",
                    "evidence": "live-osv-pypi"
                    if settings.agentcore_runtime_arn
                    else "recorded-fixture",
                    "target_version": result.candidate.target_version,
                    "tests": "actual-pytest-on-owned-fixture",
                    "tool_names": names,
                    "approval_gate_verified": True,
                    "source_unchanged": True,
                    "terminal_status": approved.status.value,
                }
            )
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001 - never expose provider bodies or credentials
        print(json.dumps({"workflow_verified": False, "error_type": type(error).__name__}))
        raise SystemExit(1) from None
