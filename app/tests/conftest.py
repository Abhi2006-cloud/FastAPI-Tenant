from collections.abc import AsyncGenerator
import os
from unittest.mock import AsyncMock, patch

# Must set before importing app modules that cache settings
os.environ["JOB_SYNC_MODE"] = "true"

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

get_settings.cache_clear()

from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def mock_redis_for_tests():
    """Prevent tests from requiring a live Redis connection."""
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)
    mock_client.get = AsyncMock(return_value=None)
    mock_client.set = AsyncMock(return_value=True)
    mock_client.setex = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=1)
    mock_client.exists = AsyncMock(return_value=0)
    mock_client.close = AsyncMock()

    mock_worker_stats = {"count": 0, "status": "stopped", "workers": []}
    mock_queue_stats = {
        "default": {"queued": 0, "started": 0, "finished": 0, "failed": 0},
        "high": {"queued": 0, "started": 0, "finished": 0, "failed": 0},
        "low": {"queued": 0, "started": 0, "finished": 0, "failed": 0},
    }

    mock_sync_redis = AsyncMock()

    with (
        patch("app.core.redis.RedisClient.get_client", return_value=mock_client),
        patch("app.core.redis.RedisClient.health_check", return_value=True),
        patch("app.core.redis.RedisClient.close", new=AsyncMock()),
        patch("app.core.rq.get_sync_redis_connection", return_value=mock_sync_redis),
        patch(
            "app.services.job_service.JobService.get_worker_stats",
            return_value=mock_worker_stats,
        ),
        patch(
            "app.services.job_service.JobService.get_queue_stats",
            return_value=mock_queue_stats,
        ),
    ):
        yield mock_client



@pytest.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
