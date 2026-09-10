"""Configuration check and local product launcher. No AWS calls in check mode."""

import argparse
import json
import os
import re
import subprocess
import sys
from contextlib import suppress
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "DEPENDENCY_SENTINEL"


def configuration():
    # Same precedence as Settings: shell wins over backend/.env.
    env = {k: v for k, v in dotenv_values(ROOT / "backend/.env").items() if v is not None}
    env.update(os.environ)
    if not env.get("AWS_PROFILE", "").strip():
        env.pop("AWS_PROFILE", None)
    sys.path.insert(0, str(ROOT / "backend"))
    from app.agent.provider import validate_provider_configuration
    from app.config import Settings

    settings = Settings()
    mode = (
        "fixture"
        if settings.fixture_mode
        else "agentcore"
        if settings.agentcore_runtime_arn
        else settings.llm_provider
    )
    errors, warnings = [], []
    if (
        not settings.fixture_mode
        and not settings.agentcore_runtime_arn
        and not settings.selected_model_id
    ):
        errors.append(
            "Set LLM_MODEL_ID for external mode, "
            "or BEDROCK_MODEL_ID / AGENTCORE_RUNTIME_ARN for AWS mode"
        )
    try:
        validate_provider_configuration(settings)
    except ValueError as error:
        errors.append(str(error))
    if settings.llm_provider == "bedrock" and settings.aws_region != "us-east-1":
        errors.append("These hackathon deployment recipes require us-east-1")
    arn = settings.agentcore_runtime_arn
    if arn and not settings.fixture_mode:
        match = re.fullmatch(
            r"arn:aws:bedrock-agentcore:([a-z0-9-]+):[0-9]{12}:runtime/[A-Za-z0-9_-]+",
            arn,
        )
        if not match or match.group(1) != settings.aws_region:
            errors.append("AgentCore runtime ARN must be valid and match the configured AWS region")
    if settings.fixture_mode and (arn or settings.selected_model_id):
        warnings.append("Fixture mode is still enabled: model/runtime settings will not be invoked")
    if arn and settings.bedrock_model_id and not settings.fixture_mode:
        warnings.append(
            "AgentCore mode: the deployed runtime's model takes precedence "
            "over local BEDROCK_MODEL_ID"
        )
    if PREFIX == "DEPENDENCY_SENTINEL":
        if not settings.repository_root.resolve().is_dir():
            errors.append(
                "DEPENDENCY_SENTINEL_REPOSITORY_ROOT must be an existing owned-repository directory"
            )
        if not settings.fixture_mode:
            warnings.append(
                "Live mode queries OSV/PyPI and may execute tests in an approved owned repository"
            )
    if not (ROOT / "frontend/dist/index.html").is_file():
        errors.append("Build frontend first: cd frontend && npm ci && npm run build")
    # Never include credential values, profile names, ARNs, input data or dotenv dumps.
    return (
        settings,
        env,
        {
            "project": ROOT.name,
            "mode": mode,
            "region": settings.aws_region,
            "configuration_valid": not errors,
            "model_access": "not_tested",
            "aws_calls_made": False,
            "errors": errors,
            "warnings": warnings,
            "storage": "local SQLite; no public hosting implied",
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "serve"], nargs="?", default="check")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--allow-paid-requests",
        action="store_true",
        help="Allow model requests; this is not a dollar spending cap",
    )
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
    # Resolve relative database/repository paths consistently even when called from elsewhere.
    os.chdir(ROOT / "backend")
    try:
        settings, env, report = configuration()
    except ValueError:
        parser.error(
            "Invalid backend/.env settings; check types and required configuration (values omitted)"
        )
    print(json.dumps(report, indent=2), flush=True)
    if not report["configuration_valid"]:
        raise SystemExit(2)
    if args.command == "check":
        return
    if not settings.fixture_mode and not args.allow_paid_requests:
        parser.error(
            "Live serving requires --allow-paid-requests; check mode never calls a provider"
        )
    env.update({f"{PREFIX}_SERVE_FRONTEND": "true", f"{PREFIX}_LOCAL_LIVE_UI": "true"})
    print(f"Local product: http://127.0.0.1:{args.port} (Ctrl+C stops it)", flush=True)
    with suppress(KeyboardInterrupt):
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.port),
            ],
            cwd=ROOT / "backend",
            env=env,
            check=True,
        )


if __name__ == "__main__":
    main()
