from collections.abc import AsyncGenerator
import os
from unittest.mock import AsyncMock, patch

# Must set before importing app modules that cache settings
os.environ["JOB_SYNC_MODE"] = "true"
os.environ["EXPOSE_INVITATION_TOKENS"] = "true"
os.environ["EMAIL_MODE"] = "development"
os.environ["EMAIL_PROVIDER"] = "console"

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

get_settings.cache_clear()


@pytest.fixture(autouse=True)
def force_test_settings():
    get_settings.cache_clear()
    settings = get_settings()
    settings.environment = "test"
    settings.job_sync_mode = True
    settings.expose_invitation_tokens = True
    settings.email_mode = "development"
    settings.email_provider = "console"
    import app.main
    app.main.settings = settings
    yield
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
    mock_client.incr = AsyncMock(return_value=1)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.close = AsyncMock()

    mock_worker_stats = {"count": 0, "status": "stopped", "workers": []}
    mock_queue_stats = {
        "default": {"queued": 0, "started": 0, "finished": 0, "failed": 0},
        "high": {"queued": 0, "started": 0, "finished": 0, "failed": 0},
        "low": {"queued": 0, "started": 0, "finished": 0, "failed": 0},
    }

    mock_sync_redis = AsyncMock()

    async def _mock_check_search_health(*args, **kwargs):
        if not get_settings().is_search_enabled:
            return "disabled"
        return "connected"

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
        patch("app.jobs.search_tasks.search_service.index_document", new=AsyncMock(return_value={"status": "ok"})),
        patch("app.jobs.search_tasks.search_service.delete_document", new=AsyncMock(return_value={"status": "ok"})),
        patch("app.infrastructure.search.health.check_search_health", side_effect=_mock_check_search_health),
    ):

        yield mock_client






from sqlalchemy.pool import StaticPool


@pytest.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=StaticPool, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    with (
        patch("app.core.database.engine", engine),
        patch("app.core.database.async_session_factory", session_factory),
        patch("app.jobs.search_tasks.async_session_factory", session_factory),
        patch("app.jobs.email_tasks.async_session_factory", session_factory),
        patch("app.jobs.tasks.async_session_factory", session_factory),
    ):
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




