"""HTTP contract for the stateless AgentCore advisory service."""

import os

from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError

from app.agent.runtime_advice import advise

app = FastAPI(title="AgentCore advisory service")


@app.get("/ping")
def ping():
    return {"status": "Healthy"}


@app.middleware("http")
async def limit_request(request: Request, call_next):
    # Limit the actual body as well as declared length before Pydantic/agent processing.
    if request.method == "POST":
        from starlette.responses import JSONResponse

        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 131072:
                return JSONResponse({"detail": "Request exceeds 128 KiB"}, status_code=413)
        request._body = bytes(body)
    return await call_next(request)


@app.post("/invocations")
def invoke(payload: dict):
    try:
        return advise(payload, fixture=os.getenv("AGENT_FIXTURE_MODE", "false") == "true")
    except ValidationError as error:
        raise HTTPException(status_code=422, detail="Invalid advisory input") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
