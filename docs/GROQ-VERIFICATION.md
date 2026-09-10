# Groq verification — September 10, 2026

Provider: Groq, through Strands' OpenAI-compatible model adapter.
Model: `openai/gpt-oss-20b`.
Inputs: fictional fixtures. Storage: temporary local SQLite.
Model calls: real inference, not recorded or scripted completions.

## Verified

The live Strands agent called lookup_advisories and lookup_release and returned CandidateSelection. It selected the upgrade supported by recorded fixture evidence, ran actual pytest in an owned temporary worktree, and completed after approval. The source repository HEAD and working tree were unchanged. This does not establish live OSV/PyPI retrieval.

A separate synthetic Strands probe verified actual read-only tool execution and
a typed structured result. The provider catalog and authentication check returned
HTTP 200. Provider credentials and raw provider error bodies were not included in
the evidence output.

## AgentCore cloud workflow

The IAM-authenticated AgentCore runtime and its DEFAULT endpoint reported READY
in us-east-1. The real cloud workflow passed using Strands and Groq GPT-OSS 20B:

- Called inspect_dependencies, lookup_advisories and lookup_release.
- Retrieved live OSV and PyPI evidence and selected Jinja2 3.1.4 → 3.1.6.
- Resolved a package environment and ran functional pytest checks in an owned
  temporary worktree.
- Paused for approval, then completed. The original source HEAD and checkout
  remained unchanged.

The live test uses the single-dependency fixture in fixtures/live-validation.
The first checks failed because the test did not resolve the proposed package
environment and assumed Jinja2 would be selected from a multi-dependency input.
Live evidence also supported a Click upgrade, which the agent selected on one
run. The corrected smoke test narrows its input; production candidate selection
still supports multiple dependencies. This is not a claim that every advisory,
repository or upgrade has been validated.

The runtime has a project-scoped execution role and Secrets Manager reference.
CloudWatch log encryption and seven-day retention were verified. The client
attempts StopRuntimeSession in a finally block; this check did not independently
measure when the session stopped.

Package validation can be rerun without AWS or a model:

```bash
cd backend
SENTINEL_RUN_PACKAGE_INTEGRATION=1 uv run pytest -q tests/test_resolved_fixture.py
```

This opt-in test accesses the package index. Ordinary tests skip it.

## Public hosting follow-up

The public application subsequently passed real AI selection, live evidence, package tests,
approval, patch export and browser-session isolation checks on September 10, 2026.
See [hosted judge access](HOSTED.md). Public execution is restricted to the included repository.

## Not established by these checks

- Safe public execution of arbitrary visitor repositories; these are deliberately rejected.
- Free access throughout the judging period or a billing hard cap.
- Model quality across a representative evaluation dataset.
- Real user adoption or any third-party system mutation.

The public demo must identify the actual hosting and model state. Do not substitute
a fixture recording for this real-model path. The authorized key must remain
server-side; rotate any credential exposed in conversation before public use.
