# Qwen integration verification — 2026-09-09

## Verified

All three applications used the real Qwen/Qwen3-8B endpoint on Modal through the
Strands SDK's OpenAI-compatible provider. Fixture-model substitution was disabled.
A separate synthetic probe verified a read-only tool call and typed output.

| Product | Real model tools observed | Workflow result |
| --- | --- | --- |
| StudyPilot | inspect_syllabus, inspect_availability, PlanningAdvice | Plan reached approval; local calendar records were absent before approval and present afterward. |
| ScamShield | inspect_message, run_local_checks, AgentAdvice | High-risk fictional SMS was assessed; the local report existed only after approval. |
| Dependency Sentinel | scan_python_manifest, lookup_advisories, lookup_release, CandidateSelection | Recorded fixture evidence led to a staged Jinja2 3.1.4 → 3.1.5 upgrade; actual fixture pytest passed, approval completed, and the source checkout remained unchanged. |

StudyPilot and ScamShield were exercised through their actual FastAPI routes using
TestClient and temporary SQLite databases. Dependency Sentinel was exercised
through its workflow service with a real command runner and a temporary owned Git
repository. The model and tool loops were real; the supplied inputs were fictional.

StudyPilot initially failed because copying the complete syllabus into a tool call
exceeded the 512-token output limit. Its advisory tools now read request-bound input
without asking the model to reproduce the document. The real workflow passed after
that change; regression tests cover request isolation and zero-argument tool schemas.

## Verification commands

Run from the product root using its configured backend environment:

```bash
backend/.venv/bin/python scripts/run.py check
backend/.venv/bin/python scripts/model_probe.py --allow-paid-requests --warm-only
backend/.venv/bin/python scripts/model_workflow_smoke.py --allow-paid-requests
```

The last two commands can start billed-capable GPU compute and require available
credit coverage. They are deliberately not part of automatic offline tests.

Offline regression totals at verification: StudyPilot 97 backend / 28 frontend;
Dependency Sentinel 167 backend / 45 frontend; ScamShield 100 backend / 23 frontend.
All three frontend builds passed. Backend tests do not call a funded model.

## Boundaries

- Dependency Sentinel's smoke test used recorded advisory/release evidence, not a
  new live OSV/PyPI audit. Its two fixture tests check the staged version declarations;
  they do not demonstrate exploit reproduction or complete application compatibility.
- Calendar and report writes are local. No external calendar, messaging service,
  pull request, or report recipient was contacted.
- The private model is deployed; the three user interfaces/backends remain local.
  This is not public hosting, an AgentCore deployment, or a completed hackathon submission.
- The model scales to zero after 120 idle seconds. A cold start took several minutes
  in these checks. Warm it shortly before use; readiness alone is not inference proof.
- The approved Modal workspace usage limit was saved as $25. The billing snapshot
  after verification reported $0 billed and $0.87 of monthly usage covered by credits
  (including prior workspace activity). Billing may lag. No card or paid plan was added.
  This record is not a guarantee about unrelated resources or future charges.
