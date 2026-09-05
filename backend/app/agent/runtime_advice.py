import os
from pathlib import Path

from strands import tool

from app.agent.model import create_strands_agent
from app.agent.orchestrator import FixtureCandidateSelector
from app.agent.runtime_evidence import evidence
from app.domain.models import CandidateSelection, PythonManifest
from app.evidence.advisories import OsvAdvisoryProvider
from app.evidence.fixtures import FixtureEvidenceStore
from app.evidence.releases import PypiReleaseProvider


def advise(payload: dict, *, fixture: bool = False):
    manifest = PythonManifest.model_validate(payload)
    if len(manifest.dependencies) > 40:
        raise ValueError("Send at most 40 locked dependencies")
    if fixture:
        provider = FixtureEvidenceStore(Path(__file__).parents[3] / "fixtures" / "evidence")
        result = FixtureCandidateSelector().select("", manifest, provider)
        return {
            "engine": "strands-fixture",
            "advice": result.model_dump(mode="json"),
            "tool_calls": ["fixture_candidate", "CandidateSelection"],
            "usage": {},
        }
    advisories = OsvAdvisoryProvider()
    releases = PypiReleaseProvider()

    @tool
    def inspect_dependencies() -> dict:
        """Read the caller's scanned dependency snapshot; no filesystem access."""
        return manifest.model_dump(mode="json")

    @tool
    def lookup_advisories(package: str, version: str) -> list[dict]:
        """Read OSV advisory evidence for a dependency present in the snapshot."""
        if not any(
            d.name == package and d.resolved_version == version for d in manifest.dependencies
        ):
            raise ValueError("Dependency is not in the supplied snapshot")
        return [a.model_dump(mode="json") for a in advisories.advisories_for(package, version)]

    @tool
    def lookup_release(package: str, version: str) -> dict:
        """Read PyPI release evidence for a dependency present in the snapshot."""
        if not any(d.name == package for d in manifest.dependencies):
            raise ValueError("Dependency is not in the supplied snapshot")
        return releases.release_for(package, version).model_dump(mode="json")

    agent = create_strands_agent(
        model_id=os.environ["BEDROCK_MODEL_ID"],
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        tools=[inspect_dependencies, lookup_advisories, lookup_release],
    )
    result = agent(
        "Inspect the dependency snapshot, look up advisories, verify a fixed release, "
        "and select one evidence-backed upgrade. Repository changes happen locally after review.",
        structured_output_model=CandidateSelection,
    )
    if not isinstance(result.structured_output, CandidateSelection):
        raise ValueError("No structured dependency candidate returned")
    return evidence(agent, result.structured_output)
