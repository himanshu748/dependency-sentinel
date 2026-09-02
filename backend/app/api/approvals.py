from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.agent.orchestrator import ApprovalGateError, DependencyUpgradeWorkflow
from app.domain.models import ApprovalChoice


class ApprovalRequest(BaseModel):
    approval_id: str
    choice: ApprovalChoice


def create_approvals_router(*, workflow: DependencyUpgradeWorkflow) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["approvals"])

    @router.post("/runs/{run_id}/approvals")
    async def decide(run_id: str, request: ApprovalRequest) -> dict:
        try:
            run = workflow.decide(
                run_id,
                approval_id=request.approval_id,
                choice=request.choice,
            )
        except KeyError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "run_not_found", "message": "Run does not exist"},
            ) from error
        except ApprovalGateError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "approval_gate_mismatch", "message": str(error)},
            ) from error
        return run.model_dump(mode="json")

    return router
