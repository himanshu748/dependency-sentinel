"""One-command, local-only, no-AWS judging demo. Run: python3 scripts/demo.py."""

import argparse
import os
import shutil
import subprocess
import tempfile
from contextlib import suppress
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "dependency-sentinel"
PREFIX = "DEPENDENCY_SENTINEL"


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Reuse installed dependencies and the existing frontend build",
    )
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
    for executable in ("uv", "npm", "git"):
        if shutil.which(executable) is None:
            parser.error(f"Install {executable} before running this demo")
    with tempfile.TemporaryDirectory(prefix=f"{ROOT.name}-demo-") as scratch:
        temporary = Path(scratch)
        env = dict(os.environ)
        env.update(
            {
                f"{PREFIX}_FIXTURE_MODE": "true",
                f"{PREFIX}_SERVE_FRONTEND": "true",
                f"{PREFIX}_DATABASE_PATH": str(temporary / "demo.sqlite3"),
                f"{PREFIX}_AGENTCORE_RUNTIME_ARN": "",
                "UV_CACHE_DIR": str(temporary / "uv-cache"),
                "AWS_EC2_METADATA_DISABLED": "true",
            }
        )
        if PROJECT == "dependency-sentinel":
            repositories = temporary / "repositories"
            repositories.mkdir()
            repository = repositories / "vulnerable-python-project"
            run(
                ["bash", str(ROOT / "scripts/create_demo_repository.sh"), str(repository)],
                cwd=ROOT,
                env=env,
            )
            env.update(
                {
                    "DEPENDENCY_SENTINEL_REPOSITORY_ROOT": str(repositories),
                    "DEPENDENCY_SENTINEL_WORKSPACE_ROOT": str(temporary / "workspaces"),
                    "DEPENDENCY_SENTINEL_EVIDENCE_FIXTURE_PATH": str(ROOT / "fixtures/evidence"),
                    "VITE_DEMO_REPOSITORY": str(repository),
                }
            )
        if not args.skip_install:
            run(["uv", "sync", "--frozen", "--dev"], cwd=ROOT / "backend", env=env)
            run(["npm", "ci"], cwd=ROOT / "frontend", env=env)
        # Dependency Sentinel embeds its isolated fixture path, so rebuild on every run.
        if not args.skip_install or PROJECT == "dependency-sentinel":
            run(["npm", "run", "build"], cwd=ROOT / "frontend", env=env)
        if not (ROOT / "frontend/dist/index.html").exists():
            parser.error("No frontend build found; rerun without --skip-install")
        python = (
            ROOT / "backend/.venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
        if not python.exists():
            parser.error("No backend environment found; rerun without --skip-install")
        print(f"Free scripted Strands demo: http://127.0.0.1:{args.port}", flush=True)
        print(
            "No live LLM inference. Ctrl+C stops the demo and removes temporary data.", flush=True
        )
        with suppress(KeyboardInterrupt):
            run(
                [
                    str(python),
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
            )


if __name__ == "__main__":
    main()
