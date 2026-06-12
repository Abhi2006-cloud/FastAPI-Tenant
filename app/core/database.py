"""
Database layer: async SQLAlchemy engine, session factory, and request-scoped sessions.

Every API route that touches the DB should depend on get_db() so each request
gets its own AsyncSession and transactions commit/rollback correctly.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# Connection pool to PostgreSQL
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
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
