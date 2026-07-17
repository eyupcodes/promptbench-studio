"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PROMPTBENCH_",
        extra="ignore",
        frozen=True,
    )

    database_url: str = "sqlite+aiosqlite:///./data/promptbench.db"
    default_judge_model: str | None = None
    request_timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    max_retries: int = Field(default=2, ge=0, le=10)
    max_concurrency: int = Field(default=5, ge=1, le=50)
    log_prompts: bool = False
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    groq_api_key: SecretStr | None = Field(default=None, validation_alias="GROQ_API_KEY")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process-wide immutable settings."""

    return Settings()
