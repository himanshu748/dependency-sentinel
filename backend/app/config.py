from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(Path(__file__).parents[1] / ".env"),
        env_prefix="DEPENDENCY_SENTINEL_",
        extra="ignore",
        populate_by_name=True,
    )

    fixture_mode: bool = True
    llm_provider: str = Field(default="bedrock", validation_alias="LLM_PROVIDER")
    llm_model_id: str | None = Field(default=None, validation_alias="LLM_MODEL_ID")
    llm_base_url: str | None = Field(default=None, validation_alias="LLM_BASE_URL")
    llm_api_key: SecretStr | None = Field(default=None, validation_alias="LLM_API_KEY")

    @field_validator("llm_provider")
    @classmethod
    def supported_provider(cls, value):
        if value not in {"bedrock", "openai-compatible"}:
            raise ValueError("LLM_PROVIDER must be bedrock or openai-compatible")
        return value

    @property
    def selected_model_id(self):
        return (
            self.llm_model_id if self.llm_provider == "openai-compatible" else self.bedrock_model_id
        )

    evidence_mode: Literal["fixture", "live"] = "fixture"
    serve_frontend: bool = False
    local_live_ui: bool = False
    agentcore_runtime_arn: str | None = None
    database_path: Path = Path("./data/dependency-sentinel.sqlite3")
    repository_root: Path = Path("../fixtures")
    workspace_root: Path = Path("./data/workspaces")
    evidence_fixture_path: Path = Path("../fixtures/evidence")
    command_timeout_seconds: int = 120
    aws_region: str = "us-east-1"
    bedrock_model_id: str | None = Field(default=None, validation_alias="BEDROCK_MODEL_ID")

    @field_validator(
        "bedrock_model_id", "agentcore_runtime_arn", "llm_model_id", "llm_base_url", mode="before"
    )
    @classmethod
    def normalize_optional_configuration(cls, value):
        return value.strip() or None if isinstance(value, str) else value
