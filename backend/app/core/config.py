from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = Field(default="Fundtracker Backend")
    app_env: str = Field(default="development")
    api_v1_prefix: str = Field(default="/api/v1")
    database_url: str = Field(default="sqlite:///./rentefond.db")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
