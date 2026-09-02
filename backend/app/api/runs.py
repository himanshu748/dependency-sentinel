from hashlib import sha256
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response, status
from pydantic import BaseModel

from app.agent.orchestrator import DependencyUpgradeWorkflow
from app.storage.sqlite import SQLiteStore


class CreateRunRequest(BaseModel):
    repository: Path


def _run_id(idempotency_key: str) -> str:
    digest = sha256(idempotency_key.encode()).hexdigest()[:24]
    return f"run-{digest}"


def create_runs_router(
    *, store: SQLiteStore, workflow: DependencyUpgradeWorkflow
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["runs"])

    @router.post("/runs")
    async def create_run(
        request: CreateRunRequest,
        response: Response,
        idempotency_key: Annotated[
            str,
            Header(alias="Idempotency-Key", min_length=1, max_length=128),
        ],
    ) -> dict:
        run_id = _run_id(idempotency_key)
        existing = store.get_run(run_id)
        if existing is not None:
            if existing.input_summary != str(request.repository):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "idempotency_conflict",
                        "message": "This idempotency key belongs to another repository",
                    },
                )
            response.status_code = status.HTTP_200_OK
            candidate_events = [
                event for event in store.list_events(run_id) if event.kind == "candidate_selected"
            ]
            approval_events = [
                event for event in store.list_events(run_id) if event.kind == "approval_required"
            ]
            return {
                "run": existing.model_dump(mode="json"),
                "candidate": candidate_events[-1].payload if candidate_events else None,
                "approval_id": (
                    approval_events[-1].payload["approval_id"] if approval_events else None
                ),
            }

        try:
            outcome = workflow.start(request.repository, run_id=run_id)
        except (OSError, RuntimeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "run_failed", "message": str(error)},
            ) from error
        response.status_code = status.HTTP_201_CREATED
        return outcome.model_dump(mode="json")

    @router.get("/runs/{run_id}")
    async def get_run(run_id: str) -> dict:
        run = store.get_run(run_id)
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "run_not_found", "message": "Run does not exist"},
            )
        return run.model_dump(mode="json")

    return router
