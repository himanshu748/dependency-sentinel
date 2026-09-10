"""External models inside AgentCore; credentials never enter invocation payloads."""

import os
import re
from functools import lru_cache

import boto3
from botocore.config import Config

from app.agent.provider import create_provider_model, validate_provider_configuration
from app.config import Settings


@lru_cache(maxsize=8)
def secret_value(arn: str, region: str) -> str:
    """Read a plain-text API key with the runtime role; cache only for this process."""
    if not re.fullmatch(
        r"arn:aws:secretsmanager:" + re.escape(region) + r":\d{12}:secret:[A-Za-z0-9/_+=.@-]+",
        arn,
    ):
        raise ValueError("LLM_API_KEY_SECRET_ARN must identify a secret in the runtime region")
    try:
        response = boto3.client(
            "secretsmanager",
            region_name=region,
            config=Config(connect_timeout=5, read_timeout=10, retries={"total_max_attempts": 1}),
        ).get_secret_value(SecretId=arn)
    except Exception:
        raise ValueError("Unable to load the configured model credential") from None
    value = response.get("SecretString")
    if not isinstance(value, str) or not value.strip() or len(value) > 16384:
        raise ValueError("Model credential must be a nonempty plain-text secret")
    return value.strip()


def runtime_model_configuration() -> dict:
    """Build from deployment configuration only, never a packaged developer .env."""
    provider = os.getenv("LLM_PROVIDER", "bedrock")
    region = os.getenv("AWS_REGION", "us-east-1")
    key = None
    if provider == "openai-compatible":
        arn = os.getenv("LLM_API_KEY_SECRET_ARN", "")
        if not arn:
            raise ValueError("External AgentCore mode requires LLM_API_KEY_SECRET_ARN")
        key = secret_value(arn, region)
    settings = Settings(
        _env_file=None,
        fixture_mode=False,
        agentcore_runtime_arn=None,
        llm_provider=provider,
        llm_model_id=os.getenv("LLM_MODEL_ID"),
        llm_base_url=os.getenv("LLM_BASE_URL"),
        llm_api_key=key,
        bedrock_model_id=os.getenv("BEDROCK_MODEL_ID"),
        aws_region=region,
    )
    validate_provider_configuration(settings)
    return {
        "model_id": settings.selected_model_id,
        "region_name": region,
        "provider_model": create_provider_model(settings),
    }
