from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.model import (
    AgentCoreCandidateSelector,
    StrandsCandidateSelector,
    create_strands_agent,
)
from app.agent.orchestrator import DependencyUpgradeWorkflow, FixtureCandidateSelector
from app.agent.provider import create_provider_model, validate_provider_configuration
from app.agent.tools import build_read_only_tools
from app.api.approvals import create_approvals_router
from app.api.events import create_events_router
from app.api.repositories import create_repositories_router
from app.api.runs import create_runs_router
from app.config import Settings
from app.evidence.advisories import OsvAdvisoryProvider
from app.evidence.fixtures import FixtureEvidenceStore
from app.evidence.releases import PypiReleaseProvider
from app.http_contract import LOCAL_ORIGIN_PATTERN, install_http_contract, runtime_metadata
from app.storage.sqlite import SQLiteStore
from app.tools.command_runner import CommandRunner


def create_app(
    settings: Settings | None = None,
    *,
    store: SQLiteStore | None = None,
    workflow: DependencyUpgradeWorkflow | None = None,
) -> FastAPI:
    active_settings = settings or Settings()
    validate_provider_configuration(active_settings)
    application = FastAPI(title="Dependency Sentinel", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_origin_regex=LOCAL_ORIGIN_PATTERN,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Idempotency-Key"],
        expose_headers=["X-Request-ID"],
    )
    install_http_contract(application)

    active_store = store or SQLiteStore(active_settings.database_path)
    active_store.initialize()
    active_workflow = workflow
    if active_workflow is None:
        repository_root = active_settings.repository_root.resolve(strict=True)
        workspace_root = active_settings.workspace_root.resolve(strict=False)
        workspace_root.mkdir(parents=True, exist_ok=True)
        if active_settings.fixture_mode:
            evidence = FixtureEvidenceStore(active_settings.evidence_fixture_path)
            selector = FixtureCandidateSelector()
            advisory_provider = evidence
            release_provider = evidence
            if active_settings.evidence_mode == "live":
                advisory_provider = OsvAdvisoryProvider()
                release_provider = PypiReleaseProvider()
        else:
            if not active_settings.selected_model_id and not active_settings.agentcore_runtime_arn:
                raise ValueError("BEDROCK_MODEL_ID is required when fixture mode is disabled")
            advisory_provider = OsvAdvisoryProvider()
            release_provider = PypiReleaseProvider()
            tools = build_read_only_tools(
                allowed_repository_root=repository_root,
                advisory_provider=advisory_provider,
                release_provider=release_provider,
            )
            if active_settings.agentcore_runtime_arn:
                selector = AgentCoreCandidateSelector(
                    active_settings.agentcore_runtime_arn, active_settings.aws_region
                )
            else:
                agent = create_strands_agent(
                    model_id=active_settings.selected_model_id,
                    provider_model=create_provider_model(active_settings),
                    region_name=active_settings.aws_region,
                    tools=tools,
                )
                selector = StrandsCandidateSelector(agent)
        runner = CommandRunner(
            allowed_root=workspace_root,
            timeout_seconds=active_settings.command_timeout_seconds,
        )
        active_workflow = DependencyUpgradeWorkflow(
            store=active_store,
            allowed_repository_root=repository_root,
            workspace_root=workspace_root,
            selector=selector,
            advisory_provider=advisory_provider,
            release_provider=release_provider,
            command_runner=runner,
            resolve_lock=active_settings.evidence_mode == "live"
            or not active_settings.fixture_mode,
            model_mode=(
                "fixture"
                if active_settings.fixture_mode
                else "agentcore"
                if active_settings.agentcore_runtime_arn
                else active_settings.llm_provider
            ),
            evidence_mode=active_settings.evidence_mode if active_settings.fixture_mode else "live",
        )

    application.state.settings = active_settings
    application.state.store = active_store
    application.state.workflow = active_workflow
    application.include_router(create_runs_router(store=active_store, workflow=active_workflow))
    application.include_router(create_events_router(store=active_store))
    application.include_router(create_approvals_router(workflow=active_workflow))
    application.include_router(
        create_repositories_router(
            allowed_repository_root=active_settings.repository_root.resolve(strict=True)
        )
    )

    @application.get("/api/health")
    async def health() -> dict[str, str | bool | int]:
        return {
            "service": "dependency-sentinel",
            "status": "ok",
            "fixture_mode": active_settings.fixture_mode,
            "model_configured": bool(active_settings.selected_model_id),
            "evidence_mode": active_settings.evidence_mode
            if active_settings.fixture_mode
            else "live",
            "repository_root": str(active_settings.repository_root.resolve()),
            **runtime_metadata(
                fixture_mode=active_settings.fixture_mode,
                runtime_arn=active_settings.agentcore_runtime_arn,
                provider=active_settings.llm_provider,
            ),
        }

    if active_settings.serve_frontend:
        from pathlib import Path

        from app.web import mount_demo_ui

        mount_demo_ui(
            application,
            fixture_mode=active_settings.fixture_mode,
            directory=Path(__file__).resolve().parents[2] / "frontend" / "dist",
            local_live_ui=active_settings.local_live_ui,
        )

    return application


app = create_app()
