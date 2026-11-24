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

    # Scientific source connector credentials (mailto / API keys for higher rate limits)
    openalex_mailto: str | None = None
    crossref_mailto: str | None = None
    pubmed_api_key: str | None = None
    arxiv_mailto: str | None = None

    # Celery / Redis for durable background jobs (P1: persistent queue).
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # When True, Celery tasks run inline (eager) instead of via broker.
    # Used in tests/dev without Redis; production keeps False for durability.
    celery_eager: bool = False

    # Celery task modules to include (imported by worker on startup).
    task_include: list[str] = [
        "packages.worker.ingest_tasks",
        "packages.worker.research_tasks",
    ]

    # Redis TLS / managed service (production). Saat diatur True, klien Redis
    # akan menggunakan koneksi TLS. Disarankan untuk Redis managed (AWS
    # ElastiCache, Azure Cache for Redis, Redis Cloud) dengan network policy
    # ketik dan secret manager untuk password.
    redis_ssl: bool = False
    redis_ssl_cert_reqs: str | None = None  # e.g. "required", "optional", "none"

    # Redis password. Dalam production, nilai ini harus diambil dari secret
    # manager, bukan dari environment file atau command line.
    redis_password: str | None = None

    @property
    def broker_url_with_password(self) -> str:
        """Bangun broker URL dengan password jika tersedia."""
        if self.redis_password:
            scheme = "rediss" if self.redis_ssl else "redis"
            return f"{scheme}://:{self.redis_password}@localhost:6379/0"
        return self.celery_broker_url

    @property
    def backend_url_with_password(self) -> str:
        """Bangun backend URL dengan password jika tersedia."""
        if self.redis_password:
            scheme = "rediss" if self.redis_ssl else "redis"
            return f"{scheme}://:{self.redis_password}@localhost:6379/0"
        return self.celery_result_backend


@lru_cache
def get_settings() -> Settings:
    return Settings()
