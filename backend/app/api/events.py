import json

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.storage.sqlite import SQLiteStore


def create_events_router(*, store: SQLiteStore) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["events"])

    def require_run(run_id: str) -> None:
        if store.get_run(run_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "run_not_found", "message": "Run does not exist"},
            )

    @router.get("/runs/{run_id}/events")
    async def list_events(run_id: str) -> list[dict]:
        require_run(run_id)
        return [event.model_dump(mode="json") for event in store.list_events(run_id)]

    @router.get("/runs/{run_id}/events/stream")
    async def stream_events(run_id: str) -> StreamingResponse:
        require_run(run_id)

        async def snapshot():
            for event in store.list_events(run_id):
                payload = json.dumps(event.model_dump(mode="json"), separators=(",", ":"))
                yield f"id: {event.sequence}\nevent: run_event\ndata: {payload}\n\n"

        return StreamingResponse(
            snapshot(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    return router
