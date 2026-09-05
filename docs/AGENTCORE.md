# Amazon Bedrock AgentCore advisory mode

The local application remains the workflow owner. AgentCore hosts the Strands advisory step and returns structured data; durable state and approvals remain local.

## Current status

Implementation and ARM64 packaging are complete. Local tests exercise the HTTP contract and the real Strands fixture tool loop. Deployment was attempted on 2026-09-05 but S3 returned `NotSignedUp`. The alternate project login is expired. No successful AgentCore invocation is claimed.

## Package and deploy

From the repository root, after installing backend dependencies:

```bash
backend/.venv/bin/python scripts/agentcore.py package
backend/.venv/bin/python scripts/agentcore.py deploy
backend/.venv/bin/python scripts/agentcore.py status
```

The script uses your standard AWS profile and `us-east-1`. It packages pinned dependencies for Python 3.12 on Linux ARM64, uploads a private zip to S3 and creates an IAM-authenticated HTTP runtime. Each project has a separate execution role. The DEFAULT endpoint is created by AgentCore; confirm its READY status before invoking.

Deployment state and archives are excluded from Git under `.agentcore/`. A failed account-activation check must be fixed in AWS before retrying. If deployment stops after creating resources, inspect the recorded state and existing AWS resources before retrying; do not create duplicates.

## Connect the local application

Use the ARN returned by the deployment in your root `.env`:

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

Nova Micro is the default model. Each model response is capped at 512 tokens, each advisory request at eight model calls, idle sessions at 60 seconds, and total session lifetime at five minutes. The client calls StopRuntimeSession in a finally block on success and failure. Runtime authentication is IAM/SigV4; there is no anonymous public model endpoint.

The initial deployment/test authorization is $5 total across all three projects. These application limits are not an AWS billing hard cap. Runtime memory, code storage and logs can incur charges; stop active sessions and remove unused project resources after judging. `scripts/agentcore.py status` also sets existing project log groups to seven-day retention.

## Evidence to capture after access is restored

1. Record the runtime and endpoint READY status.
2. Run the actual application with the runtime ARN configured.
3. Capture tool names, token usage and the approved local workflow result; do not store credentials or raw personal data.
4. Verify the remote client stopped the session.
5. Update the qualification record and architecture status only after successful cloud verification.

References: [HTTP contract](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-http-protocol-contract.html), [direct Python deployment](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy-python.html), [pricing](https://aws.amazon.com/bedrock/agentcore/pricing/).
