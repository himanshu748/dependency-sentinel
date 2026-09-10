from app.domain.models import PythonManifest

SYSTEM_PROMPT = """You are Dependency Sentinel, an evidence-first Python maintenance agent.

Choose exactly one dependency upgrade at a time. Use only the registered read-only discovery
tools. Never request a shell command, edit a source checkout, create a branch or publish a pull
request. Prefer the smallest fixed version supported by an official advisory and release record.
Return a structured candidate with the advisory identifier and a concise evidence-based rationale.
"""


def candidate_prompt(repository: str, manifest: PythonManifest | None = None) -> str:
    if manifest is not None:
        return f"""Choose one dependency upgrade from this captured Git commit manifest.

Repository label: {repository}
Authoritative manifest: {manifest.model_dump_json()}

Use the supplied dependency declarations and locked versions for selection. The source checkout
may have moved since capture; do not rescan it. Look up advisories for these locked versions and
the selected fixed release. Both forms of evidence are required. The service checks your candidate
against this captured manifest and stages and validates it at the same captured commit.
"""
    return f"""Inspect this repository and choose one safe dependency upgrade candidate:

Repository: {repository}

First inspect the repository, scan its Python manifest, look up advisories for locked versions and
look up the selected fixed release. Do not propose an upgrade without both advisory and release
evidence. The execution service will stage and validate your selection in an isolated worktree.
"""
