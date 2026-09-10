# Qwen on Modal

The three products can share one private Qwen3-8B service. Keep each product in its
own repository; do not create three GPU services for the same model.

## Deployment recipe

`scripts/modal_qwen.py` pins Qwen/Qwen3-8B revision
`b968826d9c46dd6066d109eabc6255188de91218` and vLLM 0.21.0.
It uses Hermes tool parsing and disables thinking by default for short typed advice.
Limits: one L4 GPU, zero minimum/warm containers, two target concurrent requests,
8,192-token context, two sequences, and a 120-second idle scale-down window.
Requests require a Modal proxy credential. No public anonymous inference is enabled.

Before deployment, inspect your own Modal usage limit and credits. The workspace
owner must approve any workspace-wide cap because it affects other apps.
Modal Shared Endpoints are a different per-token product; included plan credits do
not cover them. This recipe uses ordinary GPU compute instead.

Deploy **once**, from one checkout:

```bash
modal deploy --profile YOUR_PROFILE --env main scripts/modal_qwen.py
```

This is a paid-capable operation. Do not run it without credit/budget authorization.
Do not add a card or upgrade your plan as part of setup.

## Connect the local products

Use the URL returned by deployment, with /v1 appended. Each checkout includes
`scripts/modal_connect.py`; run it using that checkout's backend virtual environment.
The explicit --configure action creates one proxy credential if needed and uses
python-dotenv to update the ignored backend/.env while preserving other fields.
The file is restricted to owner read/write. Credential values are never printed.

```bash
backend/.venv/bin/python scripts/modal_connect.py \
  --base-url https://YOUR-PRIVATE-ENDPOINT.modal.direct/v1 \
  --profile YOUR_PROFILE --configure
```

For the other two checkouts, add --reuse-env with the first checkout's backend/.env
path to reuse that inference credential instead of creating new ones.
The credential belongs in the backend only, never in Vite configuration or public
submission materials. Keep access to all three backend environment files restricted.

The command selects external mode and clears only this product's AgentCore runtime
selection; existing AWS credentials and unrelated configuration are preserved.
To return to fixtures, set the project's *_FIXTURE_MODE=true.
To return to Bedrock, select LLM_PROVIDER=bedrock and configure an accessible model.

## Verify before demonstrating

```bash
backend/.venv/bin/python scripts/run.py check
backend/.venv/bin/python scripts/model_probe.py --allow-paid-requests
backend/.venv/bin/python scripts/model_workflow_smoke.py --allow-paid-requests
backend/.venv/bin/python scripts/run.py serve --port 8000 --allow-paid-requests
```

The probe sends only synthetic data. It waits up to ten minutes for a cold model,
then exercises Strands tool calling and typed output. /models requests can start
GPU compute even before inference. The script never silently substitutes fixtures.

Modal Servers return 503 while scaling from zero; cold starts are not instant.
Warm with the probe shortly before a demonstration. A successful generic probe must
still be followed by the product's real workflow and approval step. Passing offline
tests does not establish remote model quality.

The workflow smoke uses real inference and temporary local data. StudyPilot checks
that calendar records appear only after approval. ScamShield checks that its local
report appears only after approval. Dependency Sentinel uses recorded advisory and
release fixtures, runs real pytest in a temporary owned worktree, and verifies the
source checkout is unchanged. That test is not a live OSV/PyPI vulnerability audit.
It does not run exploit payloads or reproduce vulnerabilities.

The UI/backend remain local unless separately hosted. The model endpoint is private
and is not a public judge-facing product URL. The supplied AgentCore recipe remains
Bedrock-only; this setup must not be described as AgentCore deployment.

## Stop and inspect costs

Inspect the app and billing in Modal. To stop this model service, use:

```bash
modal app stop agents-for-humans-qwen --env main --profile YOUR_PROFILE
```

Do not stop other apps. The named model cache volume persists after stopping the app;
delete it only if you no longer need its weights and explicitly intend that deletion.
Do not remove a shared inference credential while another product still uses it.

Sources: [Modal server lifecycle and authentication](https://modal.com/docs/guide/servers),
[Modal budgets and spend limits](https://modal.com/docs/guide/budgets),
[Shared Endpoint credit restrictions](https://modal.com/docs/guide/shared-endpoints),
[Qwen tool-use guidance](https://github.com/QwenLM/Qwen3/blob/main/docs/source/framework/function_call.md).
