"""Offline contract tests: no provider traffic or credentials are needed."""

import json

import boto3
import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from strands import Agent, tool

from app.agent.budget import ModelCallBudget
from app.agent.provider import create_provider_model, validate_provider_configuration
from app.config import Settings

TEST_KEY = "offline-test-key-never-a-real-credential"


def external(**overrides):
    values = dict(
        _env_file=None,
        fixture_mode=False,
        llm_provider="openai-compatible",
        llm_model_id="test-model",
        llm_base_url="https://model.example.test/v1",
        llm_api_key=TEST_KEY,
        agentcore_runtime_arn=None,
    )
    values.update(overrides)
    return Settings(**values)


@pytest.mark.parametrize("field", ["llm_model_id", "llm_base_url", "llm_api_key"])
def test_external_requires_complete_configuration(field):
    with pytest.raises(ValueError, match="External mode requires"):
        validate_provider_configuration(external(**{field: None}))


@pytest.mark.parametrize(
    "url",
    [
        "http://remote.example/v1",
        "https://user:password@example.com/v1",
        "https://example.com/v1?key=private",
        "https://example.com/v1#private",
        "file:///tmp/model",
        "https://",
        "https://example.com:invalid",
    ],
)
def test_rejects_insecure_or_credential_bearing_endpoints(url):
    with pytest.raises(ValueError, match="LLM_BASE_URL"):
        validate_provider_configuration(external(llm_base_url=url))


@pytest.mark.parametrize(
    "url",
    [
        "https://model.example/v1",
        "http://127.0.0.1:9000/v1",
        "http://localhost:9000/v1",
        "http://[::1]:9000/v1",
    ],
)
def test_accepts_secure_or_loopback_endpoints(url):
    validate_provider_configuration(external(llm_base_url=url))


def test_secret_is_redacted_and_blank_key_rejected():
    assert TEST_KEY not in repr(external())
    with pytest.raises(ValueError, match="must not be blank"):
        validate_provider_configuration(external(llm_api_key="   "))


def test_external_cannot_masquerade_as_agentcore():
    with pytest.raises(ValueError, match="AgentCore currently requires"):
        validate_provider_configuration(external(agentcore_runtime_arn="runtime-placeholder"))


def test_provider_is_explicit():
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        external(llm_provider="auto")


def test_fixture_mode_never_builds_a_live_model():
    settings = external(fixture_mode=True, llm_api_key=None)
    validate_provider_configuration(settings)
    with pytest.raises(ValueError, match="explicit direct-inference"):
        create_provider_model(settings)


def test_external_factory_does_not_create_aws_clients(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("External mode must not construct AWS clients")

    monkeypatch.setattr(boto3, "client", forbidden)
    monkeypatch.setattr(boto3, "Session", forbidden)
    model = create_provider_model(external())
    assert model.config["model_id"] == "test-model"
    assert model.config["params"]["max_tokens"] == 512
    assert model.client_args["max_retries"] == 0
    assert model.client_args["timeout"] == 90.0


def test_app_wires_external_provider_and_reports_it_honestly(tmp_path, monkeypatch):
    import app.main as main
    from app.agent.model import create_strands_agent as real_factory

    calls = []

    def factory(**kwargs):
        calls.append(kwargs)
        return real_factory(**kwargs)

    monkeypatch.setattr(main, "create_strands_agent", factory)
    settings = external(
        database_path=tmp_path / "test.sqlite3",
        repository_root=tmp_path,
        workspace_root=tmp_path / "workspaces",
    )
    client = TestClient(main.create_app(settings))
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["runtime_mode"] == "openai-compatible"
    assert response.json()["aws_calls_enabled"] is False
    assert response.json()["model_access"] == "not_verified"
    assert TEST_KEY not in response.text
    assert "model.example" not in response.text
    assert len(calls) == 1
    assert calls[0]["provider_model"].config["model_id"] == "test-model"


def mock_provider_http(monkeypatch, respond):
    import openai

    real_client = openai.AsyncOpenAI

    def client(**kwargs):
        return real_client(
            **kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
        )

    monkeypatch.setattr(openai, "AsyncOpenAI", client)


def test_real_strands_tool_loop_and_structured_output_with_mock_http(monkeypatch):
    """Exercise the installed SDK protocol, not the remote model's intelligence."""
    requests = []
    tool_calls = []

    @tool
    def inspect_value(value: str) -> str:
        """Read a test value without modifying state."""
        tool_calls.append(value)
        return "observed: " + value

    class Decision(BaseModel):
        answer: str

    def respond(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert request.headers["authorization"] == "Bearer " + TEST_KEY
        assert request.url.path == "/v1/chat/completions"
        assert payload["model"] == "test-model"
        if len(requests) == 1:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_read",
                        "type": "function",
                        "function": {"name": "inspect_value", "arguments": '{"value":"sample"}'},
                    }
                ],
            }
            reason = "tool_calls"
        else:
            assert any(m["role"] == "tool" for m in payload["messages"])
            output_tool = next(
                t["function"]["name"]
                for t in payload["tools"]
                if "answer" in t["function"]["parameters"].get("properties", {})
            )
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_output",
                        "type": "function",
                        "function": {
                            "name": output_tool,
                            "arguments": '{"answer":"observed: sample"}',
                        },
                    }
                ],
            }
            reason = "tool_calls"
        return httpx.Response(
            200,
            json={
                "id": "offline-completion",
                "object": "chat.completion",
                "created": 0,
                "model": "test-model",
                "choices": [{"index": 0, "message": message, "finish_reason": reason}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    model = create_provider_model(external())
    mock_provider_http(monkeypatch, respond)
    agent = Agent(
        model=model, tools=[inspect_value], hooks=[ModelCallBudget()], callback_handler=None
    )
    result = agent("Inspect sample and report it.", structured_output_model=Decision)
    assert result.structured_output.answer == "observed: sample"
    assert tool_calls == ["sample"]
    assert len(requests) == 2


def test_remote_auth_failure_has_no_silent_fixture_fallback(monkeypatch):
    calls = []

    def denied(request):
        calls.append(request)
        return httpx.Response(401, json={"error": {"message": "Invalid test key"}})

    model = create_provider_model(external())
    mock_provider_http(monkeypatch, denied)
    from openai import AuthenticationError

    with pytest.raises(AuthenticationError):
        Agent(model=model, callback_handler=None)("Inspect this input.")
    assert len(calls) == 1
