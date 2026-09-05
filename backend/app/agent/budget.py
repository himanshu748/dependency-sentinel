"""Bound inference effort for a single advisory request."""

from strands import Agent
from strands.hooks import BeforeInvocationEvent, BeforeModelCallEvent, HookProvider


class ModelCallBudget(HookProvider):
    def __init__(self, maximum: int = 8):
        self.maximum = maximum
        self.calls = 0

    def register_hooks(self, registry):
        registry.add_callback(BeforeInvocationEvent, self.before_invocation)
        registry.add_callback(BeforeModelCallEvent, self.before_model)

    def before_invocation(self, event):
        self.calls = 0

    def before_model(self, event):
        self.calls += 1
        if self.calls > self.maximum:
            raise ValueError("Advisory request exceeded its model-call budget")


def isolated_agent(template: Agent) -> Agent:
    """Each advisory invocation starts with empty conversation history and a fresh budget."""
    return Agent(
        name=template.name,
        description=template.description,
        model=template.model,
        system_prompt=template.system_prompt,
        tools=list(template.tool_registry.registry.values()),
        callback_handler=None,
        hooks=[ModelCallBudget()],
    )
