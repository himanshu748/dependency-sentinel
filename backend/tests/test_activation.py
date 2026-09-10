"""Offline activation contract: check must never create an AWS client."""

import importlib.util
import json
import sys
from pathlib import Path

import boto3
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.http_contract import install_http_contract
from app.web import mount_demo_ui

ROOT = Path(__file__).resolve().parents[2]


def test_settings_reads_the_documented_backend_environment_file():
    assert Settings.model_config["env_file"] == ROOT / "backend" / ".env"


SPEC = importlib.util.spec_from_file_location("product_launcher", ROOT / "scripts/run.py")
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)
PREFIX = "DEPENDENCY_SENTINEL"


def test_external_configuration_check_is_offline_and_redacted(configuration, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("LLM_MODEL_ID", "offline-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://private-endpoint.example/v1")
    monkeypatch.setenv("LLM_API_KEY", "offline-secret-placeholder")
    _, _, report = launcher.configuration()
    assert report["mode"] == "openai-compatible"
    assert report["configuration_valid"]
    assert report["model_access"] == "not_tested"
    assert "offline-secret" not in json.dumps(report)
    assert "private-endpoint" not in json.dumps(report)


@pytest.fixture
def configuration(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend" / "dist").mkdir(parents=True)
    (tmp_path / "frontend" / "dist" / "index.html").write_text("<h1>Test</h1>")
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.setenv(f"{PREFIX}_FIXTURE_MODE", "false")
    monkeypatch.setenv(f"{PREFIX}_AWS_REGION", "us-east-1")
    monkeypatch.setenv(f"{PREFIX}_AGENTCORE_RUNTIME_ARN", "")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "amazon.nova-micro-v1:0")
    monkeypatch.setenv(f"{PREFIX}_REPOSITORY_ROOT", str(tmp_path))

    def forbidden(*args, **kwargs):
        raise AssertionError("Configuration check must not contact AWS")

    monkeypatch.setattr(boto3, "client", forbidden)
    monkeypatch.setattr(boto3, "Session", forbidden)


def test_direct_configuration_check_never_contacts_aws(configuration):
    _, _, report = launcher.configuration()
    assert report["mode"] == "bedrock"
    assert report["model_access"] == "not_tested"
    assert not report["aws_calls_made"]
    assert report["errors"] == []


def test_runtime_configuration_uses_agentcore(configuration, monkeypatch):
    monkeypatch.setenv(
        f"{PREFIX}_AGENTCORE_RUNTIME_ARN",
        "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/test_advisor-abc",
    )
    _, _, report = launcher.configuration()
    assert report["mode"] == "agentcore"
    assert report["configuration_valid"]
    assert "123456789012" not in json.dumps(report)


def test_runtime_wrong_region_is_rejected(configuration, monkeypatch):
    monkeypatch.setenv(
        f"{PREFIX}_AGENTCORE_RUNTIME_ARN",
        "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/test_advisor-abc",
    )
    assert not launcher.configuration()[2]["configuration_valid"]


def test_blank_model_does_not_count_as_configured(configuration, monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "   ")
    assert Settings().bedrock_model_id is None
    assert not launcher.configuration()[2]["configuration_valid"]


def test_profile_is_forwarded_without_exposure(configuration, monkeypatch):
    monkeypatch.setenv("AWS_PROFILE", "private-profile-name")
    _, env, report = launcher.configuration()
    assert env["AWS_PROFILE"] == "private-profile-name"
    assert "private-profile-name" not in json.dumps(report)


def test_missing_build_is_reported(configuration):
    (launcher.ROOT / "frontend/dist/index.html").unlink()
    assert not launcher.configuration()[2]["configuration_valid"]


def test_serve_does_not_start_live_without_cost_opt_in(configuration, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run.py", "serve"])
    with pytest.raises(SystemExit) as exc:
        launcher.main()
    assert exc.value.code == 2


def test_explicit_local_live_ui_keeps_http_boundaries(tmp_path):
    (tmp_path / "index.html").write_text("<h1>Local product</h1>")
    app = FastAPI()
    install_http_contract(app)
    mount_demo_ui(app, fixture_mode=False, local_live_ui=True, directory=tmp_path)
    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/", headers={"Host": "public.example"}).status_code == 400
    assert client.get("/", headers={"Origin": "https://public.example"}).status_code == 403
