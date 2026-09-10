# Groq + Strands on AgentCore

Status: direct Groq inference and the application workflow through AgentCore
passed on September 10, 2026, with GPT-OSS 20B. The cloud test retrieved live
OSV/PyPI evidence and validated one owned fixture upgrade. Public hosting also passed
with the included repository. See [hosted judge access](HOSTED.md) and [cloud verification](GROQ-VERIFICATION.md).

## Architecture

Browser → application API → IAM-authenticated AgentCore Runtime → Strands →
Groq's OpenAI-compatible API.

The runtime retrieves the provider key from AWS Secrets Manager using its own
execution role. Only the secret ARN is deployment configuration. The browser and
invocation payload must never contain a model key. Each project has its own
runtime and execution role.

AgentCore hosts the stateless advisory step, not the full product. Durable
application state, session isolation, validation, and user approvals still belong
to the application API. Dependency Sentinel's repository build/test runner must
remain restricted to trusted repositories in an isolated worker; do not expose
arbitrary repository command execution through a public API.

## Provider

Use `https://api.groq.com/openai/v1` with an account-authorized model supporting
local function calls, verified here with `openai/gpt-oss-20b`. Verify current model
availability and your organization's limits before deployment. Strands obtains
structured results through its output tool and Pydantic validation; this is not a
claim that Groq's native strict JSON mode supports simultaneous tool calling.

For direct local inference, use the existing private `backend/.env`:

```dotenv
LLM_PROVIDER=openai-compatible
LLM_MODEL_ID=openai/gpt-oss-20b
LLM_BASE_URL=https://api.groq.com/openai/v1
# Set LLM_API_KEY privately. Never commit or paste it into a submission.
```

Disable the project's fixture mode and clear its AgentCore runtime ARN for the
direct test. Run `scripts/model_probe.py` and `scripts/model_workflow_smoke.py`
with their explicit paid opt-in. Check their `--help` first.

## Cloud advisory runtime

Create a project-scoped plain-text Groq API-key secret in Secrets Manager in
`us-east-1`, using the AWS-managed Secrets Manager encryption key. Supply the
value through a secure input mechanism, never a command-line literal or Git file.
Creating a secret and deploying infrastructure may incur charges.

Then, from this repository:

```bash
backend/.venv/bin/python scripts/agentcore.py package
backend/.venv/bin/python scripts/agentcore.py preflight \
  --provider openai-compatible \
  --model-id openai/gpt-oss-20b \
  --base-url https://api.groq.com/openai/v1 \
  --secret-arn YOUR_PROJECT_SECRET_ARN

# Only after costs, access, secret ownership and local workflow tests are checked:
backend/.venv/bin/python scripts/agentcore.py deploy --allow-paid \
  --provider openai-compatible \
  --model-id openai/gpt-oss-20b \
  --base-url https://api.groq.com/openai/v1 \
  --secret-arn YOUR_PROJECT_SECRET_ARN
backend/.venv/bin/python scripts/agentcore.py status
```

Resolve the credential into the deployment process's `LLM_API_KEY` with
`asm-exec` or a private environment injection before paid preflight/deployment;
the deployment script does not fetch or print the secret value.

Metadata preflight does not read the key or invoke a model. Paid preflight adds
one bounded text request; it does not replace the tool-loop or product tests.
External mode checks AgentCore and the secret without requiring a Bedrock
foundation-model quota. Its execution role can read only the named secret and
has no Bedrock model invocation permission.

After READY is confirmed, configure the application with the runtime ARN,
`LLM_PROVIDER=openai-compatible`, the model ID and fixture mode disabled. The
caller does not need the Groq key. It authenticates to AgentCore with AWS IAM.
Runtime responses identify external inference as `strands-openai-compatible`.
The client rejects scripted responses and attempts session cleanup even on
failure.

## Verification gates before publishing

- Real Groq authentication, model availability, tool calls and typed output pass.
- All three end-to-end workflows pass with actual inputs and approval boundaries.
- Runtime and endpoint are READY; a real IAM-authenticated cloud invocation passes.
- Log encryption, retention, access controls and usage monitoring are verified.
- Hosted application persistence and per-user isolation pass across sessions.
- The public application calls the hosted API, not localhost.
- Judge access remains free through judging; no bring-your-own paid key requirement.
- No browser bundle, archive, log, screenshot or Git file contains credentials.
- Videos and README accurately identify the model, runtime and hosting state.

The authorized ceiling is $50 total, not a provider-enforced cap. Groq free-tier
limits are organization-specific and can change. AWS credits do not pay Groq;
AWS budgets and token limits cannot guarantee that a bank card is never charged.
Keep Modal stopped while using this route.

References: [AgentCore supports external models](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html),
[Groq OpenAI compatibility](https://console.groq.com/docs/openai),
[Groq local tool calling](https://console.groq.com/docs/tool-use/local-tool-calling).
