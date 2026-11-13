"""Application configuration using Pydantic Settings.

All settings are read from environment variables (and a `.env` file when present).
DATABASE_URL defaults to a local SQLite database so the foundation can run and be
tested without an external PostgreSQL instance. Switch to PostgreSQL by setting
DATABASE_URL in the environment; no code change is required.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "oshi"
    app_env: str = "development"
    debug: bool = True

    host: str = "127.0.0.1"
    port: int = 8000

    database_url: str = "sqlite:///./oshi_dev.db"

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()

