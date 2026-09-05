"""Offline scripted provider: exercises real Strands tool dispatch, without LLM inference."""

import json
from typing import Any

from strands import Agent
from strands.models.model import Model


class FixtureModel(Model):
    """Two-cycle deterministic model, explicitly for repeatable demonstrations."""

    def __init__(self, payload: dict, tool_name: str, output_name: str):
        self.payload = payload
        self.tool_name = tool_name
        self.output_name = output_name
        self.config = {"model_id": "offline-scripted-fixture", "context_window_limit": 200000}

    def update_config(self, **model_config: Any) -> None:
        self.config.update(model_config)

    def get_config(self) -> dict:
        return self.config

    async def structured_output(self, output_model, prompt, **kwargs):
        raise NotImplementedError("Use Agent(..., structured_output_model=...)")
        yield  # pragma: no cover

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        results = [
            block["toolResult"]
            for message in messages
            for block in message["content"]
            if "toolResult" in block
        ]
        if not results:
            name, arguments = self.tool_name, {"payload": self.payload}
        else:
            result = results[-1]
            if result.get("status") == "error":
                raise ValueError("Offline evidence tool failed")
            content = result["content"][0]
            arguments = content.get("json")
            if arguments is None:
                arguments = json.loads(content["text"])
            name = self.output_name
        yield {"messageStart": {"role": "assistant"}}
        yield {
            "contentBlockStart": {
                "contentBlockIndex": 0,
                "start": {"toolUse": {"toolUseId": f"fixture-{len(results)}", "name": name}},
            }
        }
        yield {
            "contentBlockDelta": {
                "contentBlockIndex": 0,
                "delta": {"toolUse": {"input": json.dumps(arguments)}},
            }
        }
        yield {"contentBlockStop": {"contentBlockIndex": 0}}
        yield {"messageStop": {"stopReason": "tool_use"}}
        yield {
            "metadata": {
                "usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0},
                "metrics": {"latencyMs": 0},
            }
        }


def fixture_advice(payload: dict, evidence_tool, output_model):
    agent = Agent(
        name="offline_fixture_agent",
        model=FixtureModel(payload, evidence_tool.tool_name, output_model.__name__),
        tools=[evidence_tool],
        callback_handler=None,
    )
    result = agent(
        "Run the offline evidence tool and return its validated result.",
        structured_output_model=output_model,
    )
    if not isinstance(result.structured_output, output_model):
        raise ValueError("Strands did not produce the expected fixture schema")
    return result.structured_output
