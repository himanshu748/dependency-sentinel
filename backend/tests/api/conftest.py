from pathlib import Path

import pytest

from app.agent.orchestrator import DependencyUpgradeWorkflow, FixtureCandidateSelector
from app.config import Settings
from app.evidence.fixtures import FixtureEvidenceStore
from app.main import create_app
from app.storage.sqlite import SQLiteStore
from tests.agent.test_upgrade_workflow import PassingRunner, seeded_repository

ROOT = Path(__file__).parents[3]


@pytest.fixture
def api_app(tmp_path: Path):
    repository = seeded_repository(tmp_path)
    store = SQLiteStore(tmp_path / "api.sqlite3")
    store.initialize()
    evidence = FixtureEvidenceStore(ROOT / "fixtures" / "evidence")
    workflow = DependencyUpgradeWorkflow(
        store=store,
        allowed_repository_root=tmp_path,
        workspace_root=tmp_path / "workspaces",
        selector=FixtureCandidateSelector(),
        advisory_provider=evidence,
        release_provider=evidence,
        command_runner=PassingRunner(),
    )
    settings = Settings(
        fixture_mode=True,
        database_path=tmp_path / "api.sqlite3",
        repository_root=tmp_path,
        workspace_root=tmp_path / "workspaces",
        evidence_fixture_path=ROOT / "fixtures" / "evidence",
    )
    application = create_app(settings, store=store, workflow=workflow)
    application.state.test_repository = repository
    return application
