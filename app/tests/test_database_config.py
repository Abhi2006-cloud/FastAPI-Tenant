"""Unit tests for database connection parameter builder (Neon / PgBouncer compatibility)."""

import pytest
from app.core.database import build_database_connection_params


def test_neon_pooler_url_handling():
    raw_url = "postgresql+asyncpg://user:secret@ep-cool-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=prefer"
    cleaned_url, connect_args, engine_kwargs = build_database_connection_params(
        raw_url=raw_url,
        pool_size=3,
        max_overflow=2,
        connect_timeout=30.0,
        debug=False,
    )

    # 1. sslmode and channel_binding are stripped from URL
    assert "sslmode" not in cleaned_url
    assert "channel_binding" not in cleaned_url
    assert cleaned_url == "postgresql+asyncpg://user:secret@ep-cool-pooler.us-east-2.aws.neon.tech/neondb"

    # 2. connect_args contains ssl='require', statement_cache_size=0, timeout=30.0
    assert connect_args.get("ssl") == "require"
    assert connect_args.get("statement_cache_size") == 0
    assert connect_args.get("timeout") == 30.0

    # 3. engine_kwargs contains pool settings
    assert engine_kwargs["pool_size"] == 3
    assert engine_kwargs["max_overflow"] == 2
    assert engine_kwargs["pool_pre_ping"] is True
    assert engine_kwargs["pool_recycle"] == 300
    assert engine_kwargs["connect_args"] == connect_args


def test_neon_direct_host_without_pooler():
    raw_url = "postgresql+asyncpg://user:secret@ep-cool-direct.us-east-2.aws.neon.tech/neondb?sslmode=require"
    cleaned_url, connect_args, engine_kwargs = build_database_connection_params(
        raw_url=raw_url,
        pool_size=5,
        max_overflow=10,
        connect_timeout=25.0,
    )

    assert "sslmode" not in cleaned_url
    assert connect_args.get("ssl") == "require"
    # No statement_cache_size=0 when host does not contain -pooler
    assert "statement_cache_size" not in connect_args
    assert connect_args.get("timeout") == 25.0
    assert engine_kwargs["pool_size"] == 5
    assert engine_kwargs["max_overflow"] == 10


def test_local_postgres_url():
    raw_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_workspace"
    cleaned_url, connect_args, engine_kwargs = build_database_connection_params(
        raw_url=raw_url,
    )

    assert cleaned_url == raw_url
    # Localhost should not force SSL
    assert "ssl" not in connect_args
    assert "statement_cache_size" not in connect_args
    assert connect_args.get("timeout") == 30.0


def test_sqlite_in_memory():
    raw_url = "sqlite+aiosqlite:///:memory:"
    cleaned_url, connect_args, engine_kwargs = build_database_connection_params(
        raw_url=raw_url,
    )

    assert cleaned_url == raw_url
    assert connect_args == {}
    # SQLite memory database should not receive pool_size or max_overflow
    assert "pool_size" not in engine_kwargs
    assert "max_overflow" not in engine_kwargs
    assert "connect_args" not in engine_kwargs


def test_validate_production_settings_raises_on_weak_secret():
    from app.core.config import Settings
    s = Settings(
        environment="production",
        secret_key="too-short",
        allowed_origins="https://example.com",
        database_url="postgresql+asyncpg://u:p@localhost:5432/db",
    )
    with pytest.raises(ValueError, match="at least 32 characters"):
        s.validate_production_settings()


def test_validate_production_settings_raises_on_wildcard_cors():
    from app.core.config import Settings
    s = Settings(
        environment="production",
        secret_key="a" * 32,
        allowed_origins="*",
        database_url="postgresql+asyncpg://u:p@localhost:5432/db",
    )
    with pytest.raises(ValueError, match=r"ALLOWED_ORIGINS cannot be '\*'"):
        s.validate_production_settings()


def test_validate_production_settings_succeeds_valid():
    from app.core.config import Settings
    s = Settings(
        environment="production",
        secret_key="a" * 32,
        allowed_origins="https://app.example.com",
        database_url="postgresql+asyncpg://u:p@remote-host:5432/db",
    )
    s.validate_production_settings()  # Should not raise
