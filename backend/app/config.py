from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(Path(__file__).parents[2] / ".env"),
        env_prefix="DEPENDENCY_SENTINEL_",
        extra="ignore",
        populate_by_name=True,
    )

    fixture_mode: bool = True
    database_path: Path = Path("./data/dependency-sentinel.sqlite3")
    repository_root: Path = Path("../fixtures")
    workspace_root: Path = Path("./data/workspaces")
    evidence_fixture_path: Path = Path("../fixtures/evidence")
    command_timeout_seconds: int = 120
    aws_region: str = "us-east-1"
    bedrock_model_id: str | None = Field(default=None, validation_alias="BEDROCK_MODEL_ID")
