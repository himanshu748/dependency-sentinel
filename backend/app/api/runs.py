import json
import re
from hashlib import sha256
from pathlib import Path
from threading import Lock
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response, status
from pydantic import BaseModel

from app.agent.orchestrator import DependencyUpgradeWorkflow
from app.domain.models import AgentRun, RunStatus
from app.domain.review import ReviewExportError
from app.storage.sqlite import SQLiteStore


class CreateRunRequest(BaseModel):
    repository: Path


def _run_id(idempotency_key: str) -> str:
    digest = sha256(idempotency_key.encode()).hexdigest()[:24]
    return f"run-{digest}"


def create_runs_router(*, store: SQLiteStore, workflow: DependencyUpgradeWorkflow) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["runs"])
    scan_lock = Lock()

    def existing_outcome(existing: AgentRun, request: CreateRunRequest) -> dict:
        if existing.input_summary != str(request.repository):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "idempotency_conflict",
                    "message": "This idempotency key belongs to another repository",
                },
            )
        events = store.list_events(existing.id)
        candidates = [event for event in events if event.kind == "candidate_selected"]
        approvals = [event for event in events if event.kind == "approval_required"]
        return {
            "run": existing.model_dump(mode="json"),
            "candidate": candidates[-1].payload if candidates else None,
            "approval_id": approvals[-1].payload["approval_id"] if approvals else None,
        }

    @router.post("/runs")
    def create_run(
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
            response.status_code = status.HTTP_200_OK
            return existing_outcome(existing, request)

        if not scan_lock.acquire(blocking=False):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "scan_in_progress",
                    "message": (
                        "A repository review is already running. Open Saved runs to inspect it."
                    ),
                },
            )
        try:
            existing = store.get_run(run_id)
            if existing is not None:
                response.status_code = status.HTTP_200_OK
                return existing_outcome(existing, request)
            outcome = workflow.start(request.repository, run_id=run_id)
        except (OSError, RuntimeError, ValueError) as error:
            failed_run = store.get_run(run_id)
            if failed_run is not None and failed_run.status is RunStatus.RUNNING:
                store.transition_run(run_id, RunStatus.FAILED)
            if failed_run is not None:
                store.append_event(
                    run_id,
                    kind="run_failed",
                    summary="Review stopped before completion",
                    payload={"message": str(error)},
                    idempotency_key=f"{run_id}:run_failed",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "run_failed", "message": str(error)},
            ) from error
        except HTTPException:
            raise
        except Exception as error:
            failed_run = store.get_run(run_id)
            if failed_run is not None:
                if failed_run.status is RunStatus.RUNNING:
                    store.transition_run(run_id, RunStatus.FAILED)
                store.append_event(
                    run_id,
                    kind="run_failed",
                    summary="Review stopped after an unexpected service error",
                    payload={"message": "Review incomplete. No approval was recorded."},
                    idempotency_key=f"{run_id}:run_failed",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "run_failed",
                    "message": "Review incomplete. Open Saved runs for the last recorded step.",
                },
            ) from error
        finally:
            scan_lock.release()
        response.status_code = status.HTTP_201_CREATED
        return outcome.model_dump(mode="json")

    @router.get("/runs/{run_id}")
    def get_run(run_id: str) -> dict:
        run = store.get_run(run_id)
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "run_not_found", "message": "Run does not exist"},
            )
        return run.model_dump(mode="json")

    @router.get("/runs")
    def list_runs() -> list[dict]:
        return [run.model_dump(mode="json") for run in store.list_runs()]

    def exported(run_id: str, *, receipt: bool) -> Response:
        try:
            review, patch = store.approved_export(run_id)
        except KeyError as error:
            raise HTTPException(
                status_code=404,
                detail={"code": "run_not_found", "message": "Run does not exist"},
            ) from error
        except ReviewExportError as error:
            raise HTTPException(
                status_code=409,
                detail={"code": "review_not_exportable", "message": str(error)},
            ) from error
        suffix = "review.json" if receipt else "patch"
        name = re.sub(r"[^A-Za-z0-9_-]", "_", run_id)[:80]
        return Response(
            content=json.dumps(review, indent=2, sort_keys=True) + "\n" if receipt else patch,
            media_type="application/json" if receipt else "text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="{name}.{suffix}"',
            },
        )

    @router.get("/runs/{run_id}/exports/patch", response_class=Response)
    def export_patch(run_id: str) -> Response:
        return exported(run_id, receipt=False)

    @router.get("/runs/{run_id}/exports/receipt", response_class=Response)
    def export_receipt(run_id: str) -> Response:
        return exported(run_id, receipt=True)

    return router
