from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(Path(__file__).parents[2] / ".env"),
        env_prefix="DEPENDENCY_SENTINEL_",
        extra="ignore",
    )

    fixture_mode: bool = True
    database_path: Path = Path("./data/dependency-sentinel.sqlite3")
    repository_root: Path = Path("../fixtures")
    command_timeout_seconds: int = 120
    max_model_calls: int = 12
    max_tool_calls: int = 30
    bedrock_model_id: str | None = Field(default=None, validation_alias="BEDROCK_MODEL_ID")

