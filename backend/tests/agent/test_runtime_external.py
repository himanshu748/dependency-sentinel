"""Offline checks for external providers inside AgentCore; never invoke AWS or Groq."""

import io
import json
from types import SimpleNamespace

import pytest
from strands.models.openai import OpenAIModel

from app.agent import runtime_provider
from app.agent.runtime_client import RuntimeClient
from app.agent.runtime_evidence import evidence


@pytest.fixture(autouse=True)
def clean_runtime(monkeypatch):
    for name in (
        "LLM_PROVIDER",
        "LLM_MODEL_ID",
        "LLM_BASE_URL",
        "LLM_API_KEY",
        "LLM_API_KEY_SECRET_ARN",
        "BEDROCK_MODEL_ID",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    runtime_provider.secret_value.cache_clear()


def test_bedrock_runtime_remains_supported(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "test-bedrock")
    result = runtime_provider.runtime_model_configuration()
    assert result == {
        "model_id": "test-bedrock",
        "region_name": "us-east-1",
        "provider_model": None,
    }


def test_external_runtime_requires_secret_reference_not_plaintext(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("LLM_API_KEY", "must-not-be-used")
    with pytest.raises(ValueError, match="LLM_API_KEY_SECRET_ARN"):
        runtime_provider.runtime_model_configuration()


def test_groq_runtime_uses_secret_without_bedrock(monkeypatch):
    arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:afh/groq-example"
    calls = []

    class Secrets:
        def get_secret_value(self, **kwargs):
            calls.append(kwargs)
            return {"SecretString": "offline-test-secret"}

    def client(service, **kwargs):
        assert service == "secretsmanager"
        assert kwargs["region_name"] == "us-east-1"
        return Secrets()

    monkeypatch.setattr(runtime_provider.boto3, "client", client)
    monkeypatch.setenv("LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("LLM_MODEL_ID", "llama-3.3-70b-versatile")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("LLM_API_KEY_SECRET_ARN", arn)
    result = runtime_provider.runtime_model_configuration()
    assert isinstance(result["provider_model"], OpenAIModel)
    assert result["model_id"] == "llama-3.3-70b-versatile"
    runtime_provider.runtime_model_configuration()
    assert calls == [{"SecretId": arn}]


@pytest.mark.parametrize(
    "arn", ["", "not-an-arn", "arn:aws:secretsmanager:eu-west-1:123456789012:secret:wrong"]
)
def test_invalid_secret_arn_does_not_contact_aws(arn, monkeypatch):
    monkeypatch.setattr(
        runtime_provider.boto3, "client", lambda *a, **k: pytest.fail("AWS contacted")
    )
    with pytest.raises(ValueError, match="runtime region"):
        runtime_provider.secret_value(arn, "us-east-1")


def test_secret_errors_do_not_disclose_provider_response(monkeypatch):
    class Denied:
        def get_secret_value(self, **kwargs):
            raise RuntimeError("sensitive-upstream-detail")

    monkeypatch.setattr(runtime_provider.boto3, "client", lambda *a, **k: Denied())
    with pytest.raises(ValueError) as error:
        runtime_provider.secret_value(
            "arn:aws:secretsmanager:us-east-1:123456789012:secret:afh/example", "us-east-1"
        )
    assert "sensitive-upstream-detail" not in str(error.value)


@pytest.mark.parametrize(
    "engine,accepted",
    [
        ("strands-openai-compatible", True),
        ("strands-bedrock", True),
        ("strands-fixture", False),
        ("unknown", False),
    ],
)
def test_runtime_client_accepts_live_external_and_rejects_fixture(engine, accepted):
    class Client:
        stopped = False

        def invoke_agent_runtime(self, **kwargs):
            return {
                "response": io.BytesIO(
                    json.dumps(
                        {
                            "engine": engine,
                            "advice": {"ok": True},
                            "tool_calls": ["read"],
                            "usage": {"inputTokens": 1},
                        }
                    ).encode()
                )
            }

        def stop_runtime_session(self, **kwargs):
            self.stopped = True

    client = Client()
    runtime = RuntimeClient("test-runtime", "us-east-1", client)
    if accepted:
        assert runtime.invoke({}) == {"ok": True}
    else:
        with pytest.raises(ValueError, match="live Strands"):
            runtime.invoke({})
    assert client.stopped


def test_evidence_identifies_external_model_not_bedrock():
    model = OpenAIModel(
        model_id="test", client_args={"api_key": "offline-test-secret"}, stream=False
    )
    agent = SimpleNamespace(
        model=model,
        messages=[],
        event_loop_metrics=SimpleNamespace(accumulated_usage={"inputTokens": 2}),
    )
    result = SimpleNamespace(model_dump=lambda **kwargs: {"ok": True})
    assert evidence(agent, result)["engine"] == "strands-openai-compatible"
