"""Local HTTP boundaries; this is not authentication for public hosting."""

import logging
import re
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_REQUEST_BYTES = 262_144
LOCAL_ORIGIN_PATTERN = r"https?://(localhost|127\.0\.0\.1|\[::1\])(:[0-9]+)?"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "testserver"}
logger = logging.getLogger(__name__)


class LocalApiMiddleware:
    """Bound bodies before parsing and reject browser requests from remote origins."""

    def __init__(self, app: ASGIApp, max_request_bytes: int = MAX_REQUEST_BYTES) -> None:
        self.app = app
        self.max_request_bytes = max_request_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        response_started = False

        async def safe_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                additions = [
                    (b"x-request-id", request_id.encode()),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                ]
                if scope["path"].startswith("/api/"):
                    additions.append((b"cache-control", b"no-store"))
                message = {**message, "headers": [*message.get("headers", []), *additions]}
            await send(message)

        async def reject(status: int, detail: str) -> None:
            await JSONResponse({"detail": detail, "request_id": request_id}, status_code=status)(
                scope, receive, safe_send
            )

        host = headers.get(b"host", b"").decode("latin-1")
        try:
            hostname = urlsplit("//" + host).hostname
        except ValueError:
            hostname = None
        if hostname not in LOCAL_HOSTS:
            await reject(400, "This service accepts local hosts only.")
            return
        origin = headers.get(b"origin")
        if origin is not None and not re.fullmatch(LOCAL_ORIGIN_PATTERN, origin.decode("latin-1")):
            await reject(403, "Open this application from its local address.")
            return

        # Buffer only the bounded API input. Count actual chunks as well as the
        # declared length so streamed bodies receive the same limit.
        next_receive = receive
        if scope["path"].startswith("/api/") and scope["method"] not in {"GET", "HEAD", "OPTIONS"}:
            length = headers.get(b"content-length")
            if length is not None:
                try:
                    declared = int(length)
                except ValueError:
                    await reject(400, "Invalid request length.")
                    return
                if declared < 0:
                    await reject(400, "Invalid request length.")
                    return
                if declared > self.max_request_bytes:
                    await reject(413, "Request is too large. Use less than 256 KiB.")
                    return
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > self.max_request_bytes:
                    await reject(413, "Request is too large. Use less than 256 KiB.")
                    return
                if not message.get("more_body", False):
                    break
            delivered = False

            async def replay() -> Message:
                nonlocal delivered
                if delivered:
                    return await receive()
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}

            next_receive = replay

        try:
            await self.app(scope, next_receive, safe_send)
        except Exception as error:
            # Record the type and correlation ID, never user input, provider
            # credentials or a potentially sensitive exception message.
            logger.error("request_failed request_id=%s kind=%s", request_id, type(error).__name__)
            if response_started:
                raise
            status = getattr(error, "status_code", None)
            if status in {401, 403}:
                detail = (
                    "Model access was denied. Check the backend provider credentials; "
                    "do not paste them here."
                )
            elif status == 429:
                detail = (
                    "The model provider reached a usage or capacity limit. "
                    "Check its budget and retry later."
                )
            elif status in {502, 503, 504}:
                detail = (
                    "The model endpoint is unavailable or starting up. "
                    "If it was intentionally stopped, leave it stopped; "
                    "otherwise warm it before retrying."
                )
            else:
                detail = "The local service could not finish this request. Please retry."
            await reject(503, detail)


def install_http_contract(application: FastAPI) -> None:
    application.add_middleware(LocalApiMiddleware)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        # Pydantic's default response includes rejected values; message contents,
        # syllabi and local paths must not be echoed through validation errors.
        errors = [
            {
                "loc": item["loc"],
                "msg": "Invalid value." if item["type"] == "value_error" else item["msg"],
                "type": item["type"],
            }
            for item in error.errors()
        ]
        return JSONResponse(
            {"detail": errors, "request_id": request.state.request_id}, status_code=422
        )


def runtime_metadata(
    *, fixture_mode: bool, runtime_arn: str | None, provider: str = "bedrock"
) -> dict[str, str | bool | int]:
    return {
        "runtime_mode": "local" if fixture_mode else "agentcore" if runtime_arn else provider,
        "model_access": "disabled" if fixture_mode else "not_verified",
        "storage_mode": "local_sqlite",
        "aws_calls_enabled": not fixture_mode and (bool(runtime_arn) or provider == "bedrock"),
        "max_request_bytes": MAX_REQUEST_BYTES,
    }
