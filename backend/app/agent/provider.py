"""Provider selection only; tools and consequential actions remain with the application."""

from urllib.parse import urlsplit

from app.config import Settings


def validate_provider_configuration(settings: Settings) -> None:
    if settings.fixture_mode:
        return
    if settings.agentcore_runtime_arn:
        # Model credentials belong to the remote runtime, not its caller.
        return
    if settings.llm_provider == "bedrock":
        if not settings.bedrock_model_id:
            raise ValueError("BEDROCK_MODEL_ID is required for direct Bedrock mode")
        return
    if not settings.llm_model_id or not settings.llm_base_url or not settings.llm_api_key:
        raise ValueError("External mode requires LLM_MODEL_ID, LLM_BASE_URL and LLM_API_KEY")
    if not settings.llm_api_key.get_secret_value().strip():
        raise ValueError("LLM_API_KEY must not be blank")
    try:
        url = urlsplit(settings.llm_base_url)
        _ = url.port
        valid = (
            bool(url.hostname)
            and not url.username
            and not url.password
            and not url.query
            and not url.fragment
            and (
                url.scheme == "https"
                or (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"})
            )
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(
            "LLM_BASE_URL requires HTTPS (HTTP allowed only on loopback), "
            "without credentials, query or fragment"
        )


def create_provider_model(settings: Settings):
    validate_provider_configuration(settings)
    if settings.fixture_mode or settings.agentcore_runtime_arn:
        raise ValueError("Direct model construction requires an explicit direct-inference mode")
    if settings.llm_provider == "bedrock":
        return None  # Preserve the existing Bedrock construction and defaults.
    from strands.models.openai import OpenAIModel

    return OpenAIModel(
        client_args={
            "base_url": settings.llm_base_url,
            "api_key": settings.llm_api_key.get_secret_value(),
            "max_retries": 0,
            "timeout": 90.0,
        },
        model_id=settings.llm_model_id,
        stream=False,
        params={"max_tokens": 512, "temperature": 0.0},
    )
