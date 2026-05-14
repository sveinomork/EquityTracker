from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = Field(default="EquityTracker Backend")
    app_env: str = Field(default="development")
    api_v1_prefix: str = Field(default="/api/v1")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/equitytracker"
    )
    frontend_dist_dir: str | None = Field(default=None)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance for the process lifetime."""
    return Settings()
