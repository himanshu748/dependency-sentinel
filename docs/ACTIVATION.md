# Activate the real model without changing the UI

This checkout supports scripted Strands fixtures, direct Bedrock, an IAM-authenticated
AgentCore advisory runtime, and direct OpenAI-compatible inference. The same API,
frontend, validation and human approval workflow work across them.
A configuration check does not prove model access or successful deployment.

**Bedrock access blocked?** Use the [external model setup](EXTERNAL-MODELS.md) with a
funded, tool-capable endpoint. This does not require Bedrock model access.

## Prepare once

Install the pinned backend dependencies (`cd backend && uv sync --frozen --dev`) and build
the frontend (`cd frontend && npm ci && npm run build`). Copy the root `.env.example`
to **backend/.env**, only if that file does not already exist. Never overwrite existing
credentials or settings. Do not commit that file or put AWS credentials in Vite variables.

From the repository root:

```bash
backend/.venv/bin/python scripts/run.py check
```

This command reads configuration and local paths only. It makes no AWS requests and prints
no credentials, profile names, runtime ARNs or message content. Environment variables
override backend/.env. Relative storage paths are resolved from backend/.

## Switch to direct Bedrock

In backend/.env set:

```dotenv
DEPENDENCY_SENTINEL_FIXTURE_MODE=false
DEPENDENCY_SENTINEL_AWS_REGION=us-east-1
BEDROCK_MODEL_ID=amazon.nova-micro-v1:0
LLM_PROVIDER=bedrock
DEPENDENCY_SENTINEL_AGENTCORE_RUNTIME_ARN=
# Optional named profile; otherwise use the standard AWS credential chain.
# AWS_PROFILE=your-profile
```

Use an enabled, tool-capable Bedrock model or inference profile in BEDROCK_MODEL_ID.
Model-specific structured-output behavior still needs a real workflow test.
The launcher passes the dotenv profile to the SDK process; it does not store credentials.
When launching uvicorn manually, export AWS_PROFILE in the shell.

```bash
backend/.venv/bin/python scripts/run.py check
# After access and spending coverage are verified:
backend/.venv/bin/python scripts/run.py serve --port 8000 --allow-paid-requests
```

Serving binds only to 127.0.0.1. It preserves local SQLite data across restarts.
Use a different port for each build. A healthy page means the server started,
not that the model has succeeded. User workflow actions can then incur inference costs.
There is no automatic fallback that relabels fixture output as a live model result.

Set DEPENDENCY_SENTINEL_REPOSITORY_ROOT to an existing directory containing repositories you own and trust. Live mode queries OSV/PyPI and resolves the lockfile; approving validation permits repository code to execute locally in a disposable worktree. A worktree is not a security sandbox.\n
## Switch to AgentCore

Package locally with `backend/.venv/bin/python scripts/agentcore.py package`.
The private zip uses locked Linux ARM64 dependencies and the existing /ping and
/invocations HTTP contract.

```bash
# Read-only AWS metadata. Does not invoke a model.
backend/.venv/bin/python scripts/agentcore.py preflight
# Only after spending is authorized: one bounded model probe.
backend/.venv/bin/python scripts/agentcore.py preflight --allow-paid
# Creates S3/IAM/runtime resources and runs the paid probe:
backend/.venv/bin/python scripts/agentcore.py deploy --allow-paid
backend/.venv/bin/python scripts/agentcore.py status
```

For a different direct foundation model, pass both `--model-id` and its verified
`--quota-code`. This conservative deployment recipe does not construct cross-region
inference-profile IAM policies; use direct Bedrock mode for an inference profile.

After the runtime and DEFAULT endpoint report READY, put its ARN in
DEPENDENCY_SENTINEL_AGENTCORE_RUNTIME_ARN, leave fixture mode false, check, then restart the launcher.
The deployed runtime's model takes precedence over local BEDROCK_MODEL_ID in this mode.
If provisioning partially fails, inspect .agentcore/deployment.json and AWS resources;
do not rerun blindly or create duplicate resources.

`status` only reads. `set-log-retention` explicitly sets existing runtime log groups to
seven days. Review log encryption, retention and privacy before real sensitive inputs.
Use synthetic inputs for initial verification.

## Real acceptance check after access

1. Record the selected model, region and configuration mode, without secrets.
2. Run a fresh user input through Strands and its read-only tools.
3. Verify typed advice, local deterministic validation, and the human approval gate.
4. Save/reopen the result and inspect the approved export or local action.
5. For AgentCore, record runtime/endpoint status, tool calls, usage, and session-stop evidence.
6. Test a provider failure; it must show an error, not a success or fixture substitution.
7. Record date, commit, actual outcome and limitations in docs/VERIFICATION.md.

## Spending and hosting boundaries

September 9 verification: the configuration/preflight regression tests pass without AWS
clients being created by the local checker. All three launcher smoke checks served the
UI and health endpoint successfully and rejected a remote browser origin with HTTP 403.
The read-only AWS preflight still reports Nova Micro's applied quota as zero; it stopped
before any inference or provisioning. Local smoke servers were stopped after verification.

Use **$25 total across all three builds** as the conservative current ceiling.
The earlier no-bank-charge condition remains in place. Promotional credit eligibility,
taxes and account charges require verification before paid work. Application token/session
limits and AWS Budgets are not hard dollar caps. No AWS resources are created by run.py check.

This is a local single-user app, not a public multi-user service. Do not expose its API or
repository runner through a tunnel. A public live demo needs authenticated access, per-user
storage/authorization, rate limits and a separate hosting review. AgentCore itself is
IAM-authenticated; the local app retains consequential actions.

Sources: [AgentCore direct Python deployment](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy-python.html)
and [HTTP contract](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-http-protocol-contract.html).
