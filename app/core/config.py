"""
Application configuration loaded from environment variables (.env).

Uses pydantic-settings so values like DATABASE_URL and SECRET_KEY
are validated at startup. Import get_settings() anywhere you need config.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All env-driven settings for the API. See .env.example for required keys."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AI Workspace SaaS Backend"
    debug: bool = False  # When True, SQLAlchemy logs SQL queries

    # App runtime uses async driver (asyncpg). Alembic uses sync URL (see sync_database_url).
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_workspace"
    alembic_database_url: str | None = None

    secret_key: str = "change-me-to-a-long-random-secret-key-in-production"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10

    invitation_expire_hours: int = 72

    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_host: str | None = None
    redis_port: int = 6379
    redis_password: str | None = None
    redis_db: int = 0

    # Background jobs (RQ)
    job_sync_mode: bool = False
    rq_job_timeout: int = 300
    rq_retry_max: int = 3
    rq_retry_intervals: str = "10,30,60"
    rq_result_ttl: int = 86400
    rq_failure_ttl: int = 604800

    # Meilisearch
    meilisearch_url: str | None = None
    meilisearch_api_key: str | None = None
    meilisearch_index_prefix: str = "ai_workspace"

    # Email Infrastructure
    email_mode: str = "development"  # Options: production, development, console
    email_provider: str = "console"
    resend_api_key: str | None = None
    email_from_name: str = "AI Workspace"
    email_from_address: str = "noreply@example.com"
    frontend_url: str = "http://localhost:8501"
    email_queue_name: str = "email"
    email_max_retries: int = 5
    email_rate_limit_per_hour: int = 20
    expose_invitation_tokens: bool = False

    @property
    def effective_email_mode(self) -> str:
        """Return normalized email mode ('production', 'development', or 'console')."""
        mode = (self.email_mode or "development").lower()
        if mode in ("production", "prod"):
            # If in production mode, check if provider configuration is valid
            if self.email_provider.lower() == "resend":
                key = self.resend_api_key
                if key and not key.startswith("<") and key != "RESEND_API_KEY":
                    return "production"
            # Fallback to development if production provider is missing valid credentials
            return "development"
        if mode in ("console", "test"):
            return "console"
        return "development"

    @property
    def is_production_email_enabled(self) -> bool:
        """True only if production email mode is active with valid provider configuration."""
        return self.effective_email_mode == "production"

    @property
    def rq_retry_interval_list(self) -> list[int]:
        """Parse comma-separated retry intervals into seconds."""
        return [int(x.strip()) for x in self.rq_retry_intervals.split(",") if x.strip()]

    @property
    def sync_database_url(self) -> str:
        """Alembic migrations need a sync driver URL (no +asyncpg)."""
        if self.alembic_database_url:
            return self.alembic_database_url
        return self.database_url.replace("+asyncpg", "")

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — read .env once per process."""
    return Settings()
