"""The local launcher must not inherit a live evidence setting."""

import importlib.util
from pathlib import Path


def test_demo_overrides_live_evidence_and_model_environment(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("sentinel_demo", root / "scripts/demo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    monkeypatch.setenv("DEPENDENCY_SENTINEL_EVIDENCE_MODE", "live")
    monkeypatch.setenv("DEPENDENCY_SENTINEL_FIXTURE_MODE", "false")
    monkeypatch.setenv("DEPENDENCY_SENTINEL_AGENTCORE_RUNTIME_ARN", "must-not-be-used")
    monkeypatch.setattr("sys.argv", ["demo.py", "--skip-install", "--port", "8212"])
    monkeypatch.setattr(module.shutil, "which", lambda executable: f"/tools/{executable}")
    monkeypatch.setattr(Path, "exists", lambda path: True)
    monkeypatch.setattr(
        module, "run", lambda command, *, cwd, env: calls.append((command, env.copy()))
    )

    module.main()

    server_command, environment = calls[-1]
    assert "uvicorn" in server_command
    assert environment["DEPENDENCY_SENTINEL_EVIDENCE_MODE"] == "fixture"
    assert environment["DEPENDENCY_SENTINEL_FIXTURE_MODE"] == "true"
    assert environment["DEPENDENCY_SENTINEL_AGENTCORE_RUNTIME_ARN"] == ""
    assert environment["AWS_EC2_METADATA_DISABLED"] == "true"
    assert environment["DEPENDENCY_SENTINEL_DATABASE_PATH"].endswith("demo.sqlite3")
