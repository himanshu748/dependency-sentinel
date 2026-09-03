from pathlib import Path

from strands import Agent

from app.agent.model import create_strands_agent
from app.agent.tools import build_read_only_tools
from app.evidence.fixtures import FixtureEvidenceStore

ROOT = Path(__file__).parents[3]


def test_strands_agent_registers_only_read_only_discovery_tools(tmp_path: Path) -> None:
    evidence = FixtureEvidenceStore(ROOT / "fixtures" / "evidence")
    tools = build_read_only_tools(
        allowed_repository_root=tmp_path,
        advisory_provider=evidence,
        release_provider=evidence,
    )

    agent = create_strands_agent(
        model_id="amazon.nova-lite-v1:0",
        region_name="us-east-1",
        tools=tools,
    )

    assert isinstance(agent, Agent)
    assert agent.model.config["max_tokens"] == 512
    assert set(agent.tool_names) == {
        "inspect_repository",
        "scan_python_manifest",
        "lookup_advisories",
        "lookup_release",
    }
    assert "run_shell" not in agent.tool_names
