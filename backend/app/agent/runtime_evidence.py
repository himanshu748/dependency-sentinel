"""Return invocation evidence without recording raw prompts or credentials."""


def evidence(agent, result):
    calls = [
        block["toolUse"]["name"]
        for message in agent.messages
        for block in message["content"]
        if "toolUse" in block
    ]
    return {
        "engine": "strands-bedrock",
        "advice": result.model_dump(mode="json"),
        "tool_calls": calls,
        "usage": agent.event_loop_metrics.accumulated_usage,
    }
