# Hosted judge access

Open https://dependency-sentinel.34-233-68-117.sslip.io/#overview and enter the workspace.
No account, payment, or API key is required from the visitor.
Use fictional or non-sensitive inputs.

## Actual runtime

The public React application calls its same-origin FastAPI gateway on an AWS
Graviton EC2 host in us-east-1. The host uses an IAM role to invoke this project's
AgentCore runtime. Strands calls Groq's GPT-OSS 20B with read-only tools; the
application validates the result and requires approval before its final action.
Model credentials stay in Secrets Manager and are read only by the runtime role.
This is not a claim of Bedrock foundation-model inference access.

## Session storage and limits

- Records are stored on the server in separate browser-session SQLite stores.
- A Secure, HttpOnly cookie grants access to that session. Clearing it loses access.
- There is no account recovery or cross-device sync. Session access lasts up to 35 days.
- AI requests: 10 per session/day, 20 per IP/day, 50 per app/day, 1,500 per app lifetime.
  Failed attempts count. These are request limits, not dollar-denominated billing caps.
- Approvals and saved-record reads do not consume the AI allowance.
- New sessions and HTTP requests are also rate-limited; reuse an existing session.
- The service has one small shared host, not a high-availability production deployment.
  Model-provider quotas, transient failures and maintenance can affect availability.

Dependency Sentinel's public build executes only the included owned Python repository.
Its live OSV/PyPI checks, dependency resolution and package tests run in an isolated
worktree. Approval enables patch export; it does not modify the source checkout.
Use the local build for other trusted repositories.

## Verification on September 10, 2026

Public HTTPS and the real AI workflow passed, including the approval gate and a
second browser session being unable to read the first session's record.
Chromium checks at 1440×1000 and 390×844 passed page identity, meaningful content,
no framework overlay, no console errors, navigation from landing to workspace,
and no horizontal overflow.

StudyPilot produced an approved calendar; ScamShield generated a report only after
approval; Dependency Sentinel passed its owned-fixture tests and exported a patch
only after approval. These checks used fictional inputs, not a broad quality benchmark.

The public host is deployed. Video publication, Builder posts, repository push and
the Devpost submission are separate release steps; deployment does not prove them.
