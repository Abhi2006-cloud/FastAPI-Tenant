"""
Database layer: async SQLAlchemy engine, session factory, and request-scoped sessions.

Every API route that touches the DB should depend on get_db() so each request
gets its own AsyncSession and transactions commit/rollback correctly.
"""

from collections.abc import AsyncGenerator
from typing import Any
import urllib.parse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()


def build_database_connection_params(
    raw_url: str,
    pool_size: int = 3,
    max_overflow: int = 2,
    connect_timeout: float = 30.0,
    debug: bool = False,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """
    Build sanitized database URL, connect_args, and create_async_engine kwargs.

    - Strips 'sslmode', 'ssl', and 'channel_binding' query parameters that asyncpg rejects.
    - Sets connect_args ssl='require' when host is non-local.
    - Sets connect_args statement_cache_size=0 when host contains '-pooler' (PgBouncer compatibility).
    - Sets connect_args timeout (default 30s) to handle serverless cold starts (Neon).
    - Preserves compatibility with SQLite databases for unit tests.
    """
    parsed = urllib.parse.urlsplit(raw_url)
    connect_args: dict[str, Any] = {}
    engine_kwargs: dict[str, Any] = {
        "echo": debug,
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    is_sqlite = parsed.scheme.startswith("sqlite")
    if is_sqlite:
        if ":memory:" in raw_url:
            from sqlalchemy.pool import StaticPool
            engine_kwargs["poolclass"] = StaticPool
        return raw_url, {}, engine_kwargs

    engine_kwargs["pool_size"] = pool_size
    engine_kwargs["max_overflow"] = max_overflow

    # Strip query parameters that cause issues with asyncpg
    cleaned_query = ""
    original_sslmode = None
    if parsed.query:
        query_params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if "sslmode" in query_params:
            original_sslmode = query_params.pop("sslmode")[-1]
        if "ssl" in query_params:
            if not original_sslmode:
                original_sslmode = query_params.pop("ssl")[-1]
            else:
                query_params.pop("ssl")
        if "channel_binding" in query_params:
            query_params.pop("channel_binding")

        cleaned_query = urllib.parse.urlencode(query_params, doseq=True)

    scheme = parsed.scheme
    if scheme in ("postgres", "postgresql", "postgresql+psycopg2"):
        scheme = "postgresql+asyncpg"

    cleaned_url = urllib.parse.urlunsplit(
        (scheme, parsed.netloc, parsed.path, cleaned_query, parsed.fragment)
    )

    is_asyncpg = "asyncpg" in scheme or scheme.startswith("postgresql")
    if is_asyncpg and not is_sqlite:
        host = parsed.hostname or ""
        is_local = host in ("localhost", "127.0.0.1", "::1", "")

        if original_sslmode == "disable":
            pass
        elif not is_local or original_sslmode in ("require", "verify-ca", "verify-full"):
            connect_args["ssl"] = "require"

        if "-pooler" in host:
            connect_args["statement_cache_size"] = 0

        connect_args["timeout"] = connect_timeout

    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    return cleaned_url, connect_args, engine_kwargs


# Build parameters using configuration
_db_url, _connect_args, _engine_kwargs = build_database_connection_params(
    raw_url=settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    connect_timeout=settings.db_connect_timeout,
    debug=settings.debug,
)

# Connection pool to PostgreSQL
engine = create_async_engine(
    _db_url,
    **_engine_kwargs,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Dedicated NullPool engine for background worker tasks (RQ, threads, asyncio.run).
# Asyncpg connection objects are strictly bound to a single asyncio event loop.
# Using NullPool ensures background tasks running in separate or ephemeral event loops
# (such as an embedded worker thread or per-task asyncio.run) open a dedicated connection
# on that loop and close it immediately upon exit without returning it to the main web pool.
_worker_engine_kwargs = dict(_engine_kwargs)
_worker_engine_kwargs.pop("pool_size", None)
_worker_engine_kwargs.pop("max_overflow", None)
if _worker_engine_kwargs.get("poolclass") is None:
    _worker_engine_kwargs["poolclass"] = NullPool

worker_engine = create_async_engine(
    _db_url,
    **_worker_engine_kwargs,
)

worker_session_factory = async_sessionmaker(
    worker_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models (User, Organization, etc.)."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: yields one DB session per HTTP request.

    - On success: commits the transaction after the route finishes.
    - On error: rolls back and re-raises.
    Inject with: db: Annotated[AsyncSession, Depends(get_db)]
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
