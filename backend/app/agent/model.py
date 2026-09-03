from collections.abc import Sequence
from typing import Any

from strands import Agent
from strands.models import BedrockModel

from app.agent.prompts import SYSTEM_PROMPT, candidate_prompt
from app.domain.models import CandidateSelection, PythonManifest


def create_strands_agent(
    *,
    model_id: str,
    region_name: str,
    tools: Sequence[Any],
) -> Agent:
    model = BedrockModel(
        model_id=model_id,
        region_name=region_name,
        temperature=0.0,
        max_tokens=512,
    )
    return Agent(
        name="dependency_sentinel",
        description="Selects one evidence-backed Python dependency upgrade",
        model=model,
        tools=list(tools),
        system_prompt=SYSTEM_PROMPT,
        callback_handler=None,
    )


class StrandsCandidateSelector:
    def __init__(self, agent: Agent) -> None:
        self.agent = agent

    def select(
        self,
        repository: str,
        manifest: PythonManifest,
        advisory_provider: object,
    ) -> CandidateSelection:
        del manifest, advisory_provider
        result = self.agent(
            candidate_prompt(repository),
            structured_output_model=CandidateSelection,
        )
        if not isinstance(result.structured_output, CandidateSelection):
            raise ValueError("Strands agent did not return a dependency candidate")
        return result.structured_output
