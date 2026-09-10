# Amazon Bedrock AgentCore advisory mode

For a model outside Bedrock, use [Groq + Strands on AgentCore](GROQ-AGENTCORE.md).
The external-provider runtime is deployed with Secrets Manager credentials.
The real Groq application workflow through AgentCore passed on September 10, 2026.

For the current configuration-only handoff, read [ACTIVATION.md](ACTIVATION.md).
Checks are read-only by default; paid probes and deployment require explicit opt-in.

The local application remains the workflow owner. AgentCore hosts the Strands advisory step and returns structured data; durable state and approvals remain local.

## Current status

The IAM-authenticated runtime and DEFAULT endpoint reported READY in us-east-1.
The application completed an approved fixture upgrade through AgentCore, Strands
and Groq GPT-OSS 20B, with live OSV/PyPI evidence and resolved-package pytest.
See [the evidence and its limits](GROQ-VERIFICATION.md).
The earlier Nova Micro quota issue does not block this external-model route.
Repository validation and durable state remain local; this is not a public
full-application deployment.

## Package and deploy

From the repository root, after installing backend dependencies:

```bash
backend/.venv/bin/python scripts/agentcore.py package
backend/.venv/bin/python scripts/agentcore.py preflight
backend/.venv/bin/python scripts/agentcore.py deploy --allow-paid
backend/.venv/bin/python scripts/agentcore.py status
```

The script uses your standard AWS profile and `us-east-1`. It packages pinned dependencies for Python 3.12 on Linux ARM64, uploads a private zip to S3 and creates an IAM-authenticated HTTP runtime. Each project has a separate execution role. The DEFAULT endpoint is created by AgentCore; confirm its READY status before invoking.

Deployment state and archives are excluded from Git under `.agentcore/`. A failed account-activation check must be fixed in AWS before retrying. If deployment stops after creating resources, inspect the recorded state and existing AWS resources before retrying; do not create duplicates.

## Connect the local application

Use the ARN returned by the deployment in your `backend/.env`:

```dotenv
DEPENDENCY_SENTINEL_FIXTURE_MODE=false
DEPENDENCY_SENTINEL_AGENTCORE_RUNTIME_ARN=arn-returned-by-your-deployment
DEPENDENCY_SENTINEL_AWS_REGION=us-east-1
AWS_PROFILE=your-activated-profile
```

Leave fixture mode true to use the offline Strands demo. Without a runtime ARN, live mode uses the direct Bedrock model provider and requires `BEDROCK_MODEL_ID`.

For local HTTP contract testing without AWS:

```bash
cd backend
AGENT_FIXTURE_MODE=true uv run uvicorn app.agent.runtime_http:app --host 127.0.0.1 --port 8080
```

GET `/ping` reports health. POST `/invocations` accepts the project-specific advisory schema in `app/agent/runtime_advice.py`. Invalid input is rejected before inference. The direct-code entrypoint binds on 8080 inside AgentCore.

## Cost and lifecycle controls

The verified deployment uses Groq GPT-OSS 20B; the script's Bedrock default remains
Nova Micro. Each model response is capped at 512 tokens, each advisory request at
eight model calls, idle sessions at 60 seconds, and total session lifetime at five
minutes. The client attempts StopRuntimeSession in a finally block on success and
failure. Runtime authentication is IAM/SigV4; there is no anonymous public model
endpoint. Logs have KMS encryption and seven-day retention.

Use $50 total across all three projects as the authorized spending ceiling, not a target. These limits are not an AWS billing hard cap or a guarantee against bank charges. Runtime memory, code storage, logs and applicable taxes can incur charges. `status` is read-only; `set-log-retention` is the separate explicit operation for seven-day retention.

## Evidence to capture after access is restored

1. Record the runtime and endpoint READY status.
2. Run the actual application with the runtime ARN configured.
3. Capture tool names, token usage and the approved local workflow result; do not store credentials or raw personal data.
4. Verify the remote client stopped the session.
5. Update the qualification record and architecture status only after successful cloud verification.

References: [HTTP contract](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-http-protocol-contract.html), [direct Python deployment](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy-python.html), [pricing](https://aws.amazon.com/bedrock/agentcore/pricing/).
