import time
from typing import Any
from collections.abc import AsyncGenerator
import os
from unittest.mock import AsyncMock, patch

# Must set before importing app modules that cache settings
os.environ["JOB_SYNC_MODE"] = "true"
os.environ["EXPOSE_INVITATION_TOKENS"] = "true"
os.environ["EMAIL_MODE"] = "development"
os.environ["EMAIL_PROVIDER"] = "console"
os.environ["PLATFORM_ADMIN_EMAILS"] = "platform-admin@example.com,platform-admin-2@example.com"

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

get_settings.cache_clear()


class FakeRedisPipeline:
    def __init__(self, fake_redis: "FakeRedis"):
        self.fake_redis = fake_redis
        self.commands: list[tuple] = []

    def incr(self, key: str, amount: int = 1):
        self.commands.append(("incr", key, amount))
        return self

    def expire(self, key: str, seconds: int):
        self.commands.append(("expire", key, seconds))
        return self

    def get(self, key: str):
        self.commands.append(("get", key))
        return self

    def set(self, key: str, value: Any):
        self.commands.append(("set", key, value))
        return self

    async def execute(self):
        results = []
        for cmd in self.commands:
            action = cmd[0]
            if action == "incr":
                results.append(await self.fake_redis.incr(cmd[1], cmd[2]))
            elif action == "expire":
                results.append(await self.fake_redis.expire(cmd[1], cmd[2]))
            elif action == "get":
                results.append(await self.fake_redis.get(cmd[1]))
            elif action == "set":
                results.append(await self.fake_redis.set(cmd[1], cmd[2]))
        self.commands = []
        return results


class FakeRedis:
    def __init__(self):
        self._data: dict[str, str] = {}
        self._ttls: dict[str, float] = {}

    def _is_expired(self, key: str) -> bool:
        if key in self._ttls:
            if time.time() > self._ttls[key]:
                self._data.pop(key, None)
                self._ttls.pop(key, None)
                return True
        return False

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        if self._is_expired(key):
            return None
        return self._data.get(key)

    async def set(self, key: str, value: Any) -> bool:
        self._data[key] = str(value)
        return True

    async def setex(self, key: str, time_sec: int, value: Any) -> bool:
        self._data[key] = str(value)
        self._ttls[key] = time.time() + time_sec
        return True

    async def incr(self, key: str, amount: int = 1) -> int:
        if self._is_expired(key):
            self._data[key] = "0"
        val = int(self._data.get(key, 0)) + amount
        self._data[key] = str(val)
        return val

    async def expire(self, key: str, seconds: int) -> bool:
        if key in self._data:
            self._ttls[key] = time.time() + seconds
            return True
        return False

    async def ttl(self, key: str) -> int:
        if key not in self._data or self._is_expired(key):
            return -2
        if key in self._ttls:
            return max(0, int(self._ttls[key] - time.time()))
        return -1

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._data:
                del self._data[k]
                self._ttls.pop(k, None)
                count += 1
        return count

    async def exists(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if not self._is_expired(k) and k in self._data:
                count += 1
        return count

    def pipeline(self) -> FakeRedisPipeline:
        return FakeRedisPipeline(self)

    async def close(self) -> None:
        pass


@pytest.fixture(autouse=True)
def force_test_settings():
    get_settings.cache_clear()
    settings = get_settings()
    settings.environment = "test"
    settings.job_sync_mode = True
    settings.expose_invitation_tokens = True
    settings.email_mode = "development"
    settings.email_provider = "console"
    settings.platform_admin_emails = "platform-admin@example.com"
    import app.main
    app.main.settings = settings
    yield
    get_settings.cache_clear()


from app.core.database import Base, get_db
from app.main import app


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def fake_redis_instance():
    return FakeRedis()


@pytest.fixture(autouse=True)
def mock_redis_for_tests(fake_redis_instance):
    """Provide realistic in-memory FakeRedis for rate-limiting, session revocation, and quotas."""
    mock_client = fake_redis_instance

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
        patch("app.core.redis.RedisClient.get_client", new=AsyncMock(return_value=mock_client)),
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
        patch("app.core.database.worker_engine", engine),
        patch("app.core.database.worker_session_factory", session_factory),
        patch("app.jobs.search_tasks.async_session_factory", session_factory),
        patch("app.jobs.email_tasks.async_session_factory", session_factory),
        patch("app.jobs.tasks.async_session_factory", session_factory),
        patch("app.infrastructure.search.service.async_session_factory", session_factory),
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
    get_settings().platform_admin_emails = "platform-admin@example.com,platform-admin-2@example.com"
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


@pytest.fixture
async def two_tenants(client: AsyncClient) -> dict:
    """Fixture providing Tenant A, Tenant B, and Platform Admin accounts for cross-tenant testing."""
    get_settings().platform_admin_emails = "platform-admin@example.com,platform-admin-2@example.com"

    async def create_actor(email: str):
        pwd = "Password123!"
        r1 = await client.post("/auth/register", json={"email": email, "password": pwd})
        assert r1.status_code == 201, r1.text
        r2 = await client.post("/auth/login", json={"email": email, "password": pwd})
        assert r2.status_code == 200, r2.text
        data = r2.json()
        return {
            "email": email,
            "user_id": r1.json()["id"],
            "token": data["access_token"],
            "session_id": data["session_id"],
            "headers": {"Authorization": f"Bearer {data['access_token']}"},
        }

    p_admin = await create_actor("platform-admin@example.com")

    # ── Tenant A Setup ────────────────────────────────────────────────────────
    owner_a = await create_actor("owner-a@example.com")
    resp_org_a = await client.post(
        "/organizations",
        json={"name": "Tenant Alpha"},
        headers=owner_a["headers"],
    )
    assert resp_org_a.status_code == 201, resp_org_a.text
    org_a = resp_org_a.json()
    org_a_id = org_a["id"]
    owner_a["headers"]["X-Organization-Id"] = org_a_id

    admin_a = await create_actor("admin-a@example.com")
    inv_admin_a = await client.post(
        f"/organizations/{org_a_id}/invite",
        json={"email": admin_a["email"]},
        headers=owner_a["headers"],
    )
    assert inv_admin_a.status_code == 201, inv_admin_a.text
    token_inv_a = inv_admin_a.json()["token"]
    await client.post(
        "/invitations/accept",
        json={"token": token_inv_a},
        headers=admin_a["headers"],
    )
    await client.patch(
        f"/memberships/{admin_a['user_id']}/role",
        json={"role": "admin"},
        headers=owner_a["headers"],
    )
    admin_a["headers"]["X-Organization-Id"] = org_a_id

    member_a = await create_actor("member-a@example.com")
    inv_mem_a = await client.post(
        f"/organizations/{org_a_id}/invite",
        json={"email": member_a["email"]},
        headers=owner_a["headers"],
    )
    assert inv_mem_a.status_code == 201, inv_mem_a.text
    await client.post(
        "/invitations/accept",
        json={"token": inv_mem_a.json()["token"]},
        headers=member_a["headers"],
    )
    member_a["headers"]["X-Organization-Id"] = org_a_id

    # ── Tenant B Setup ────────────────────────────────────────────────────────
    owner_b = await create_actor("owner-b@example.com")
    resp_org_b = await client.post(
        "/organizations",
        json={"name": "Tenant Beta"},
        headers=owner_b["headers"],
    )
    assert resp_org_b.status_code == 201, resp_org_b.text
    org_b = resp_org_b.json()
    org_b_id = org_b["id"]
    owner_b["headers"]["X-Organization-Id"] = org_b_id

    admin_b = await create_actor("admin-b@example.com")
    inv_admin_b = await client.post(
        f"/organizations/{org_b_id}/invite",
        json={"email": admin_b["email"]},
        headers=owner_b["headers"],
    )
    assert inv_admin_b.status_code == 201, inv_admin_b.text
    await client.post(
        "/invitations/accept",
        json={"token": inv_admin_b.json()["token"]},
        headers=admin_b["headers"],
    )
    await client.patch(
        f"/memberships/{admin_b['user_id']}/role",
        json={"role": "admin"},
        headers=owner_b["headers"],
    )
    admin_b["headers"]["X-Organization-Id"] = org_b_id

    member_b = await create_actor("member-b@example.com")
    inv_mem_b = await client.post(
        f"/organizations/{org_b_id}/invite",
        json={"email": member_b["email"]},
        headers=owner_b["headers"],
    )
    assert inv_mem_b.status_code == 201, inv_mem_b.text
    await client.post(
        "/invitations/accept",
        json={"token": inv_mem_b.json()["token"]},
        headers=member_b["headers"],
    )
    member_b["headers"]["X-Organization-Id"] = org_b_id

    return {
        "tenant_a": {
            "org_id": org_a_id,
            "org_name": "Tenant Alpha",
            "owner": owner_a,
            "admin": admin_a,
            "member": member_a,
        },
        "tenant_b": {
            "org_id": org_b_id,
            "org_name": "Tenant Beta",
            "owner": owner_b,
            "admin": admin_b,
            "member": member_b,
        },
        "platform_admin": p_admin,
    }




