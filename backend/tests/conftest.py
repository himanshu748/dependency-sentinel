"""Keep automated tests offline even when the developer has enabled a real model."""
import os
from pathlib import Path


def pytest_configure(config):
    del config
    os.environ["DEPENDENCY_SENTINEL_FIXTURE_MODE"] = "true"
    os.environ["DEPENDENCY_SENTINEL_AGENTCORE_RUNTIME_ARN"] = ""
    root = Path(__file__).resolve().parents[2]
    os.environ["DEPENDENCY_SENTINEL_REPOSITORY_ROOT"] = str(root / "fixtures")
    os.environ["DEPENDENCY_SENTINEL_EVIDENCE_FIXTURE_PATH"] = str(root / "fixtures/evidence")
    os.environ["DEPENDENCY_SENTINEL_EVIDENCE_MODE"] = "fixture"
    os.environ["LLM_PROVIDER"] = "bedrock"
    os.environ["BEDROCK_MODEL_ID"] = ""
    os.environ["AWS_EC2_METADATA_DISABLED"] = "true"
