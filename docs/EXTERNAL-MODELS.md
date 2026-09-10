# External models without Bedrock access

The local backend can use Strands with an OpenAI-compatible Chat Completions endpoint.
This changes only model inference: tools, typed output validation, local storage and
human approval boundaries remain in the application. It does not deploy AgentCore
or make the product publicly accessible.

## Configure a funded endpoint

In the existing **backend/.env**, set the following without overwriting other settings:

```dotenv
DEPENDENCY_SENTINEL_FIXTURE_MODE=false
DEPENDENCY_SENTINEL_AGENTCORE_RUNTIME_ARN=
LLM_PROVIDER=openai-compatible
LLM_MODEL_ID=your-actual-served-model
LLM_BASE_URL=https://your-verified-endpoint/v1
LLM_API_KEY=your-private-inference-credential
```

These are placeholders, not a usable endpoint. Keep the key server-side and out of Git,
Vite variables, screenshots and chat. The model must support OpenAI-style function
calling, tool results, tool choice and JSON-schema tool arguments. A text-only model
is insufficient. The adapter uses non-streaming requests, temperature 0 and a 512-token
output limit. Model-specific support must be verified before using real customer data.

HTTPS is required except for loopback development endpoints. URLs containing embedded
credentials, query parameters or fragments are rejected. Set all three LLM fields;
there is no automatic switch to another provider or fixture answers on failure.

From the repository root:

```bash
# Install the pinned OpenAI adapter dependency.
(cd backend && uv sync --frozen --dev)
backend/.venv/bin/python scripts/run.py check
# Only after confirming provider funding and permission for paid requests:
backend/.venv/bin/python scripts/run.py serve --port 8000 --allow-paid-requests
```

A configuration check and /api/health make no inference request. Health reports
openai-compatible, model_access=not_verified and aws_calls_enabled=false.
The last field does NOT mean there are no external model requests or charges.

## Modal-specific notes

For the pinned, private Qwen3-8B deployment and smoke test, see [Qwen on Modal](MODAL.md).

Use the exact base URL, served model ID and inference credential supplied by your
endpoint. Do not substitute a Modal CLI management token for inference authentication.
This adapter sends a Bearer credential; an endpoint requiring other headers needs
a separate, tested authentication adapter.

Modal-hosted vLLM needs a model-compatible chat template and tool-call parser.
Having a GPU or an OpenAI-shaped URL does not by itself establish agent compatibility.
No Modal GPU resource is created by these scripts.

AWS promotional credits do not pay Modal or another model provider. Check that provider's
balance and billing controls before starting compute. The app's model-call budget and
token limit reduce request size; they are not a dollar cap or a guarantee against charges.
AgentCore + external-provider configuration is intentionally rejected: the supplied
AgentCore recipe remains Bedrock-only.

## Verification before submission

1. Confirm check passes without printing secrets.
2. Run one small synthetic request through the actual product. Confirm the model uses
   a registered tool and returns schema-valid advice, then exercise the approval step.
3. Confirm the provider usage record and inspect failure behavior with invalid input.
4. Save a real workflow recording and provide judge-accessible instructions or hosting.
   A localhost URL on the developer's machine is not judge access.
5. Describe the actual model host accurately. Do not label external inference as Bedrock
   or claim AgentCore hosting without a verified deployment.

Offline tests cover configuration rejection, secret redaction, application wiring, the
installed Strands tool loop and typed output over mocked HTTP, and an authentication
failure with no fixture fallback. They do not establish model quality, provider access,
remaining credits or production readiness.

References: [Strands OpenAI provider](https://strandsagents.com/docs/user-guide/concepts/model-providers/openai/),
[Modal vLLM serving example](https://modal.com/docs/examples/vllm_inference).
