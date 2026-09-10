"""Deployment must fail closed before creating chargeable infrastructure."""

import importlib.util
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

SPEC = importlib.util.spec_from_file_location(
    "agentcore_deploy", Path(__file__).resolve().parents[3] / "scripts" / "agentcore.py"
)
deployment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deployment)


class FakeAWS:
    def __init__(self, quota=1000, authorized=True, fail_inference=False):
        self.quota = quota
        self.authorized = authorized
        self.fail_inference = fail_inference
        self.clients = []
        self.probes = []

    def client(self, name, **kwargs):
        self.clients.append(name)
        if name == "bedrock-runtime":
            assert kwargs["config"].retries["total_max_attempts"] == 1
        assert name in {"sts", "bedrock", "service-quotas", "bedrock-runtime"}
        return self

    def get_caller_identity(self):
        return {"Account": "123456789012"}

    def get_foundation_model_availability(self, **kwargs):
        assert kwargs["modelId"] == deployment.MODEL
        return {
            "authorizationStatus": "AUTHORIZED" if self.authorized else "NOT_AUTHORIZED",
            "regionAvailability": "AVAILABLE",
            "entitlementAvailability": "AVAILABLE",
            "agreementAvailability": {"status": "AVAILABLE"},
        }

    def get_service_quota(self, **kwargs):
        assert kwargs == {"ServiceCode": "bedrock", "QuotaCode": "L-D2912E70"}
        return {"Quota": {"Value": self.quota}}

    def converse(self, **kwargs):
        self.probes.append(kwargs)
        if self.fail_inference:
            raise ClientError(
                {"Error": {"Code": "ThrottlingException", "Message": "daily quota"}},
                "Converse",
            )
        return {
            "output": {"message": {"content": [{"text": "OK"}]}},
            "usage": {"inputTokens": 4, "outputTokens": 1},
        }


def test_zero_quota_prevents_inference():
    aws = FakeAWS(quota=0)
    with pytest.raises(SystemExit, match="quota is zero"):
        deployment.preflight(aws)
    assert aws.probes == []


def test_unauthorized_model_prevents_inference():
    aws = FakeAWS(authorized=False)
    with pytest.raises(SystemExit, match="model is not available"):
        deployment.preflight(aws)
    assert aws.clients == ["sts", "bedrock"]


def test_inference_probe_is_bounded_and_preserves_usage():
    aws = FakeAWS()
    result = deployment.preflight(aws, allow_inference=True)
    assert len(aws.probes) == 1
    assert aws.probes[0]["inferenceConfig"] == {"maxTokens": 8, "temperature": 0}
    assert result["usage"]["outputTokens"] == 1
    assert result["account"] == "123456789012"


def test_inference_failure_is_not_reported_as_ready():
    with pytest.raises(SystemExit, match="ThrottlingException"):
        deployment.preflight(FakeAWS(fail_inference=True), allow_inference=True)


def test_deploy_stops_before_s3_or_iam_when_quota_is_zero(tmp_path, monkeypatch):
    aws = FakeAWS(quota=0)
    archive = tmp_path / "deployment.zip"
    archive.touch()
    monkeypatch.setattr(deployment, "BUILD", tmp_path)
    monkeypatch.setattr(deployment, "STATE", tmp_path / "deployment.json")
    monkeypatch.setattr(deployment.boto3, "Session", lambda **kwargs: aws)
    with pytest.raises(SystemExit, match="quota is zero"):
        deployment.deploy(allow_paid=True)
    assert not (tmp_path / "deployment.json").exists()
    assert "s3" not in aws.clients
    assert "iam" not in aws.clients


def test_preflight_is_metadata_only_by_default():
    aws = FakeAWS()
    result = deployment.preflight(aws)
    assert result["inference_verified"] is False
    assert "bedrock-runtime" not in aws.clients
    assert aws.probes == []


def test_deployment_requires_explicit_cost_opt_in(monkeypatch):
    def forbidden(**kwargs):
        raise AssertionError("AWS must not be contacted")

    monkeypatch.setattr(deployment.boto3, "Session", forbidden)
    with pytest.raises(SystemExit, match="allow-paid"):
        deployment.deploy()


def test_status_is_read_only(tmp_path, monkeypatch):
    import json

    state = tmp_path / "deployment.json"
    state.write_text(json.dumps({"id": "test_runtime", "region": "us-east-1"}))
    monkeypatch.setattr(deployment, "STATE", state)

    class ReadOnly:
        def get_agent_runtime(self, **kwargs):
            return {"status": "READY"}

        def list_agent_runtime_endpoints(self, **kwargs):
            return {"runtimeEndpoints": []}

    def client(service, **kwargs):
        assert service == "bedrock-agentcore-control"
        return ReadOnly()

    monkeypatch.setattr(deployment.boto3, "client", client)
    deployment.status()
    assert json.loads(state.read_text()) == {"id": "test_runtime", "region": "us-east-1"}


class ExternalAWS:
    def __init__(self):
        self.clients = []
        self.secret_reads = 0

    def client(self, name, **kwargs):
        self.clients.append(name)
        assert name in {"sts", "secretsmanager", "bedrock-agentcore-control"}
        return self

    def get_caller_identity(self):
        return {"Account": "123456789012"}

    def describe_secret(self, **kwargs):
        return {"ARN": kwargs["SecretId"]}

    def list_agent_runtimes(self, **kwargs):
        assert kwargs == {"maxResults": 1}
        return {"agentRuntimes": []}

    def get_secret_value(self, **kwargs):
        self.secret_reads += 1
        return {"SecretString": "offline-test-secret"}


def configure_external(monkeypatch):
    monkeypatch.setattr(deployment, "PROVIDER", "openai-compatible")
    monkeypatch.setattr(deployment, "MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setattr(deployment, "BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setattr(
        deployment,
        "SECRET_ARN",
        "arn:aws:secretsmanager:us-east-1:123456789012:secret:afh/groq-example",
    )


def test_external_preflight_does_not_require_bedrock_or_read_key(monkeypatch):
    configure_external(monkeypatch)
    aws = ExternalAWS()
    result = deployment.preflight(aws)
    assert result["bedrock_model_access_required"] is False
    assert result["inference_verified"] is False
    assert aws.secret_reads == 0
    assert "bedrock" not in aws.clients
    assert "service-quotas" not in aws.clients


def test_external_preflight_rejects_foreign_secret_before_lookup(monkeypatch):
    configure_external(monkeypatch)
    monkeypatch.setattr(
        deployment,
        "SECRET_ARN",
        "arn:aws:secretsmanager:us-east-1:999999999999:secret:wrong-account",
    )
    aws = ExternalAWS()
    with pytest.raises(SystemExit, match="this account and region"):
        deployment.preflight(aws)
    assert aws.clients == ["sts"]


def test_external_preflight_rejects_loopback_for_cloud(monkeypatch):
    configure_external(monkeypatch)
    monkeypatch.setattr(deployment, "BASE_URL", "http://localhost:9000/v1")
    with pytest.raises(SystemExit, match="HTTPS"):
        deployment.preflight(ExternalAWS())


def test_external_probe_is_bounded_and_does_not_report_credentials(monkeypatch):
    from types import SimpleNamespace

    import openai

    configure_external(monkeypatch)
    monkeypatch.setenv("LLM_API_KEY", "offline-test-secret")
    probes = []

    class Provider:
        def __init__(self, **kwargs):
            assert kwargs["max_retries"] == 0
            assert kwargs["api_key"] == "offline-test-secret"
            self.chat = SimpleNamespace(completions=self)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def create(self, **kwargs):
            probes.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="OK"))],
                usage=SimpleNamespace(model_dump=lambda: {"total_tokens": 5}),
            )

    monkeypatch.setattr(openai, "OpenAI", Provider)
    aws = ExternalAWS()
    result = deployment.preflight(aws, allow_inference=True)
    assert result["inference_verified"] is True
    assert aws.secret_reads == 0
    assert probes[0]["max_tokens"] == 128
    assert "offline-test-secret" not in str(result)
