"""Explicit paid synthetic smoke check for the configured direct model endpoint."""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agent.budget import ModelCallBudget
from app.agent.provider import (
    create_provider_model,
    validate_provider_configuration,
)
from app.config import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-paid-requests", action="store_true")
    parser.add_argument("--warm-only", action="store_true")
    args = parser.parse_args()
    if not args.allow_paid_requests:
        parser.error("Model calls and cold starts require --allow-paid-requests")
    settings = Settings()
    validate_provider_configuration(settings)
    if settings.fixture_mode or settings.llm_provider != "openai-compatible":
        parser.error("This check requires explicit external-model configuration")
    # /models can start a GPU container on a scale-to-zero endpoint.
    with httpx.Client(timeout=20, follow_redirects=False) as client:
        deadline = time.monotonic() + 600
        attempt = 0
        while time.monotonic() < deadline:
            attempt += 1
            try:
                response = client.get(
                    settings.llm_base_url.rstrip("/") + "/models",
                    headers={
                        "Authorization": "Bearer "
                        + settings.llm_api_key.get_secret_value()
                    },
                )
                if response.status_code == 200:
                    ids = [item.get("id") for item in response.json().get("data", [])]
                    if settings.llm_model_id not in ids:
                        raise RuntimeError("Configured model is not advertised")
                    break
                if response.status_code not in {429, 502, 503, 504}:
                    raise RuntimeError(
                        "Endpoint readiness failed: HTTP " + str(response.status_code)
                    )
            except httpx.TimeoutException:
                pass
            if attempt % 3 == 1:
                print(
                    json.dumps({"model_ready": False, "attempt": attempt}), flush=True
                )
            time.sleep(10)
        else:
            raise TimeoutError("Endpoint did not become ready within 10 minutes")
    if args.warm_only:
        print(json.dumps({"model_ready": True, "inference_verified": False}))
        return
    from pydantic import BaseModel
    from strands import Agent, tool

    observed = []

    @tool
    def inspect_probe(token: str) -> str:
        """Read the synthetic probe value. This tool has no side effects."""
        observed.append(token)
        return "verified:" + token

    class ProbeResult(BaseModel):
        value: str

    agent = Agent(
        model=create_provider_model(settings),
        tools=[inspect_probe],
        callback_handler=None,
        hooks=[ModelCallBudget(maximum=4)],
    )
    result = agent(
        "Call inspect_probe with token alpha. Return its exact result in the value field. "
        "You must call the tool; do not guess its output.",
        structured_output_model=ProbeResult,
    )
    if observed != ["alpha"] or result.structured_output.value != "verified:alpha":
        raise RuntimeError("Tool/structured-output verification failed")
    print(
        json.dumps(
            {
                "model_ready": True,
                "inference_verified": True,
                "model": settings.llm_model_id,
                "tool_calls": len(observed),
                "structured_output_valid": True,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001 - redact provider error bodies
        # Never print provider exception bodies: they may contain request headers or customer data.
        print(
            json.dumps({"verified": False, "error_type": type(error).__name__}),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
