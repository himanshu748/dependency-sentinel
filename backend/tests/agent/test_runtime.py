import io
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from strands import tool

from app.agent.fixture_model import fixture_advice
from app.agent.runtime_client import RuntimeClient
from app.agent.runtime_http import app


def test_fixture_executes_registered_strands_tool():
    called = []

    class Answer(BaseModel):
        count: int

    @tool
    def inspect_fixture(payload: dict) -> dict:
        """Inspect supplied fixture values without a model network call."""
        called.append(payload)
        return {"count": len(payload["items"])}

    result = fixture_advice({"items": [1, 2, 3]}, inspect_fixture, Answer)
    assert result.count == 3
    assert called == [{"items": [1, 2, 3]}]


def test_runtime_health_and_invalid_input(monkeypatch):
    monkeypatch.setenv("AGENT_FIXTURE_MODE", "true")
    with TestClient(app) as client:
        assert client.get("/ping").json() == {"status": "Healthy"}
        assert client.post("/invocations", json={}).status_code == 422
        assert client.post("/invocations", content=b"x" * 131073).status_code == 413


def test_runtime_client_stops_session_and_validates_engine():
    class Client:
        stopped = None

        def invoke_agent_runtime(self, **kwargs):
            self.session = kwargs["runtimeSessionId"]
            assert kwargs["qualifier"] == "DEFAULT"
            return {
                "response": io.BytesIO(
                    json.dumps(
                        {
                            "engine": "strands-bedrock",
                            "advice": {"answer": 3},
                            "tool_calls": ["inspect"],
                            "usage": {"inputTokens": 10},
                        }
                    ).encode()
                )
            }

        def stop_runtime_session(self, **kwargs):
            self.stopped = kwargs["runtimeSessionId"]

    client = Client()
    runtime = RuntimeClient("test-arn", "us-east-1", client)
    assert runtime.invoke({"question": "fixture"}) == {"answer": 3}
    assert client.stopped == client.session
    assert runtime.last_evidence["tool_calls"] == ["inspect"]


def test_runtime_client_stops_session_after_invocation_failure():
    class Client:
        stopped = False

        def invoke_agent_runtime(self, **kwargs):
            raise ValueError("unavailable")

        def stop_runtime_session(self, **kwargs):
            self.stopped = True

    client = Client()
    with pytest.raises(ValueError, match="unavailable"):
        RuntimeClient("test-arn", "us-east-1", client).invoke({})
    assert client.stopped


def test_runtime_fixture_returns_candidate(monkeypatch):
    monkeypatch.setenv("AGENT_FIXTURE_MODE", "true")
    with TestClient(app) as client:
        response = client.post(
            "/invocations",
            json={
                "project_name": "fixture",
                "requires_python": ">=3.11",
                "dependencies": [
                    {
                        "name": "jinja2",
                        "ecosystem": "pypi",
                        "declared_requirement": "jinja2==3.1.4",
                        "resolved_version": "3.1.4",
                    }
                ],
            },
        )
    assert response.status_code == 200
    assert response.json()["engine"] == "strands-fixture"
    assert response.json()["advice"]["target_version"] == "3.1.5"
