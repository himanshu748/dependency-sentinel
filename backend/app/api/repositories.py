from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.tools.repository import RepositoryBoundaryError, inspect_repository


class InspectRepositoryRequest(BaseModel):
    repository: Path


def create_repositories_router(*, allowed_repository_root: Path) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["repositories"])

    @router.post("/repositories/inspect")
    async def inspect_route(request: InspectRepositoryRequest) -> dict:
        try:
            snapshot = inspect_repository(
                request.repository,
                allowed_root=allowed_repository_root,
            )
        except (OSError, RepositoryBoundaryError) as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "repository_invalid", "message": str(error)},
            ) from error
        return snapshot.model_dump(mode="json")

    return router
