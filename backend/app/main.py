from fastapi import FastAPI

from app.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings()
    application = FastAPI(title="Dependency Sentinel", version="0.1.0")

    @application.get("/api/health")
    async def health() -> dict[str, str | bool]:
        return {
            "service": "dependency-sentinel",
            "status": "ok",
            "fixture_mode": active_settings.fixture_mode,
            "model_configured": bool(active_settings.bedrock_model_id),
        }

    return application


app = create_app()
