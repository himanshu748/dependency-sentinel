"""Public judge gateway: opaque sessions, per-session stores and persistent quotas.

Run one uvicorn worker behind a trusted HTTPS reverse proxy. Never expose the
ordinary local app directly. Only the configured owned repository can execute.
"""

import asyncio
import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles

COOKIE = "__Host-afh_session"
MAX_BODY = 65_536
SESSION_SECONDS = 35 * 86400


class Registry:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.root / "sessions.sqlite3"
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS counters (key TEXT PRIMARY KEY, count INTEGER NOT NULL);
            """)

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def reserve(self, limits):
        """Reserve every counter atomically, including failed/aborted model attempts."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            for key, limit in limits:
                row = db.execute("SELECT count FROM counters WHERE key=?", (key,)).fetchone()
                if row and row[0] >= limit:
                    return False
            for key, _ in limits:
                db.execute(
                    "INSERT INTO counters VALUES (?,1) ON CONFLICT(key) "
                    "DO UPDATE SET count=count+1",
                    (key,),
                )
        return True

    def session(self, token):
        if token and re.fullmatch(r"[0-9a-f]{64}", token):
            identity = hashlib.sha256(token.encode()).hexdigest()
            with self.connect() as db:
                row = db.execute("SELECT created FROM sessions WHERE id=?", (identity,)).fetchone()
            if row and row[0] > time.time() - SESSION_SECONDS:
                return identity
        return None

    def create(self):
        token = secrets.token_hex(32)
        identity = hashlib.sha256(token.encode()).hexdigest()
        with self.connect() as db:
            db.execute("INSERT INTO sessions VALUES (?,?)", (identity, time.time()))
        return token, identity


class HostedGateway:
    def __init__(
        self,
        *,
        origin,
        root,
        factory,
        static_directory,
        project,
        owned_repository=None,
        daily_limit=50,
        session_limit=10,
        total_limit=1500,
    ):
        parsed = urlsplit(origin)
        if parsed.scheme != "https" or not parsed.netloc or parsed.path or parsed.query:
            raise ValueError("Configure one exact HTTPS public origin")
        self.origin = origin
        self.host = parsed.netloc
        self.root = Path(root)
        self.registry = Registry(root)
        self.factory = factory
        self.static = StaticFiles(directory=static_directory, html=True)
        self.project = project
        self.repository = str(Path(owned_repository).resolve()) if owned_repository else None
        self.daily_limit = daily_limit
        self.session_limit = session_limit
        self.total_limit = total_limit
        self.write_lock = asyncio.Lock()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                event = await receive()
                if event["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif event["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        if scope["type"] != "http":
            return
        headers = dict(scope.get("headers", []))
        path, method = scope["path"], scope["method"]
        cookie = None

        async def protected_send(message):
            if message["type"] == "http.response.start":
                safe_headers = [
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-frame-options", b"DENY"),
                    (b"strict-transport-security", b"max-age=31536000"),
                    (
                        b"content-security-policy",
                        b"default-src 'self'; script-src 'self'; "
                        b"style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                        b"connect-src 'self'; font-src 'self' data:; frame-ancestors 'none'; "
                        b"base-uri 'none'; form-action 'self'",
                    ),
                ]
                if cookie:
                    safe_headers.append((b"set-cookie", cookie.encode()))
                names = {key for key, _ in safe_headers}
                message = {
                    **message,
                    "headers": [
                        (k, v) for k, v in message.get("headers", []) if k.lower() not in names
                    ]
                    + safe_headers,
                }
            await send(message)

        async def respond(code, detail):
            await JSONResponse({"detail": detail}, status_code=code)(scope, receive, protected_send)

        async def serve_static():
            try:
                await self.static(scope, receive, protected_send)
            except HTTPException as error:
                await respond(
                    error.status_code,
                    "Not found." if error.status_code == 404 else "Request not supported.",
                )

        if headers.get(b"host", b"").decode("latin-1") != self.host:
            return await respond(400, "Unknown host.")
        if scope.get("scheme") != "https":
            return await respond(400, "HTTPS is required.")
        if method not in {"GET", "HEAD", "POST", "DELETE"}:
            return await respond(405, "Method not supported.")
        if path in {"/docs", "/redoc", "/openapi.json"}:
            return await respond(404, "Not found.")
        if headers.get(b"sec-fetch-site") == b"cross-site":
            return await respond(403, "Use this application's own page.")
        if method in {"POST", "DELETE"}:
            if headers.get(b"origin", b"").decode("latin-1") != self.origin:
                return await respond(403, "A same-origin request is required.")
            if method == "POST" and not headers.get(b"content-type", b"").startswith(
                b"application/json"
            ):
                return await respond(415, "Send JSON.")

        # Only proxy-authenticated client addresses are trusted; uvicorn listens
        # on loopback and accepts forwarded headers only from the local proxy.
        address = (scope.get("client") or ("unknown", 0))[0]
        ip = hashlib.sha256((self.host + address).encode()).hexdigest()
        day, minute = int(time.time() // 86400), int(time.time() // 60)
        if not self.registry.reserve([(f"http:{day}:{minute}:{ip}", 240)]):
            return await respond(429, "Too many requests. Retry in one minute.")

        jar = SimpleCookie()
        try:
            jar.load(headers.get(b"cookie", b"").decode("latin-1"))
        except Exception:
            return await respond(400, "Invalid session cookie.")
        token = jar[COOKIE].value if COOKIE in jar else None
        identity = self.registry.session(token)
        if not identity:
            if method not in {"GET", "HEAD"}:
                return await respond(401, "Open the application to start a private session.")
            if path.startswith("/assets/"):
                return await serve_static()
            if not self.registry.reserve(
                [(f"new-session:{day}:{ip}", 20), ("sessions:total", 1500)]
            ):
                return await respond(
                    429, "Session capacity reached. Reuse an existing browser session."
                )
            token, identity = self.registry.create()
            cookie = (
                f"{COOKIE}={token}; Path=/; Secure; HttpOnly; SameSite=Strict; "
                f"Max-Age={SESSION_SECONDS}"
            )

        if not path.startswith("/api/"):
            return await serve_static()
        if path == "/api/health" and method == "GET":
            return await JSONResponse(
                {
                    "service": self.project,
                    "status": "ok",
                    "hosted": True,
                    "fixture_mode": False,
                    "model_configured": True,
                    "runtime_mode": "agentcore",
                    "model_access": "not_verified",
                    "storage_mode": "session_sqlite",
                    "aws_calls_enabled": True,
                    "max_request_bytes": MAX_BODY,
                    **({"evidence_mode": "live"} if self.repository else {}),
                }
            )(scope, receive, protected_send)
        if path == "/api/hosting" and method == "GET":
            return await JSONResponse(
                {
                    "hosted": True,
                    "provider": "Groq",
                    "model": "openai/gpt-oss-20b",
                    "runtime": "AgentCore + Strands",
                    "storage": "private browser-session database",
                    "session_daily_requests": self.session_limit,
                    "project_daily_requests": self.daily_limit,
                    "repository": self.repository,
                    "notice": "No login or API key needed. Use fictional or non-sensitive inputs. "
                    "Keep this browser session to return to your records.",
                }
            )(scope, receive, protected_send)

        body = bytearray()
        if method in {"POST", "DELETE"}:
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > MAX_BODY:
                    return await respond(413, "Input exceeds the hosted 64 KiB limit.")
                if not message.get("more_body"):
                    break
            if self.repository and path in {"/api/runs", "/api/repositories/inspect"}:
                try:
                    value = json.loads(body)
                except (ValueError, UnicodeDecodeError):
                    return await respond(422, "Invalid JSON.")
                if not isinstance(value, dict) or value.get("repository") != self.repository:
                    return await respond(
                        403,
                        "Hosted reviews use only the included repository. "
                        "Use the local build for your own trusted repositories.",
                    )
            if (
                self.repository
                and path.startswith("/api/repositories/")
                and path != "/api/repositories/inspect"
            ):
                return await respond(403, "Repository import is local-only.")

        inference = method == "POST" and path in {"/api/plans", "/api/cases", "/api/runs"}
        if method in {"POST", "DELETE"}:
            if self.write_lock.locked():
                return await respond(409, "Another request is running. Retry shortly.")
            await self.write_lock.acquire()
        app = None
        try:
            if inference and not self.registry.reserve(
                [
                    (f"model-session:{day}:{identity}", self.session_limit),
                    (f"model-ip:{day}:{ip}", self.session_limit * 2),
                    (f"model-day:{day}", self.daily_limit),
                    ("model:total", self.total_limit),
                ]
            ):
                return await respond(
                    429,
                    "Today's hosted AI allowance is used. "
                    "Saved records and approvals remain available.",
                )
            directory = self.root / identity
            directory.mkdir(mode=0o700, exist_ok=True)
            app = self.factory(directory)
            internal = dict(scope)
            # Public validation above is separate from the local application's
            # loopback-only HTTP contract. No untrusted forwarded headers survive.
            internal["headers"] = [
                (k, v)
                for k, v in scope["headers"]
                if k.lower()
                not in {
                    b"host",
                    b"origin",
                    b"cookie",
                    b"x-forwarded-host",
                    b"x-forwarded-proto",
                    b"x-forwarded-for",
                }
            ] + [(b"host", b"localhost")]
            delivered = False

            async def replay():
                nonlocal delivered
                if delivered or method not in {"POST", "DELETE"}:
                    return await receive()
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}

            await app(internal, replay, protected_send)
        finally:
            if app is not None:
                connection = getattr(app.state.store, "_connection", None)
                if connection is not None:
                    connection.close()
            if method in {"POST", "DELETE"}:
                self.write_lock.release()


def create_hosted_app():
    """Factory mode avoids reading provider secrets or a developer's dotenv."""
    from app.config import Settings
    from app.main import create_app

    root = Path(__file__).resolve().parents[2]
    settings = Settings(_env_file=None, serve_frontend=False)
    if settings.fixture_mode or not settings.agentcore_runtime_arn:
        raise ValueError("Public hosting requires an explicit live AgentCore runtime")
    data = Path(os.environ["AFH_DATA_ROOT"])
    owned = os.environ.get("AFH_OWNED_REPOSITORY")

    def factory(directory):
        overrides = {"database_path": directory / "records.sqlite3", "serve_frontend": False}
        if root.name == "dependency-sentinel":
            if not owned:
                raise ValueError("Hosted Sentinel requires the included repository")
            overrides.update(
                repository_root=Path(owned).parent,
                workspace_root=directory / "workspaces",
                evidence_mode="live",
            )
        return create_app(settings.model_copy(update=overrides))

    return HostedGateway(
        origin=os.environ["AFH_PUBLIC_ORIGIN"],
        root=data,
        factory=factory,
        static_directory=root / "frontend/dist",
        project=root.name,
        owned_repository=owned,
    )
