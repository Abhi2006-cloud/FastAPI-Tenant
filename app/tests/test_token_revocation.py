from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.redis import RedisClient


@pytest.mark.asyncio
async def test_access_token_revocation_on_logout(client: AsyncClient):
    """Access token is immediately revoked upon logout via Redis sid blacklist."""
    email = "revoketest@example.com"
    pwd = "Password123!"
    await client.post("/auth/register", json={"email": email, "password": pwd})
    login_res = await client.post("/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    access_token = login_res.json()["access_token"]
    refresh_token = login_res.json()["refresh_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    # Access token works before logout
    me_res = await client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200

    # Logout revokes the session
    logout_res = await client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
        headers=headers,
    )
    assert logout_res.status_code == 204

    # Same access token is now rejected with 401
    me_after = await client.get("/auth/me", headers=headers)
    assert me_after.status_code == 401
    assert "revoked" in me_after.text.lower() or "credentials" in me_after.text.lower()


@pytest.mark.asyncio
async def test_access_token_revocation_on_logout_all(client: AsyncClient):
    """Logging out of all sessions revokes all access tokens."""
    email = "revokeall@example.com"
    pwd = "Password123!"
    await client.post("/auth/register", json={"email": email, "password": pwd})

    # Device 1
    l1 = await client.post("/auth/login", json={"email": email, "password": pwd})
    t1 = l1.json()["access_token"]

    # Device 2
    l2 = await client.post("/auth/login", json={"email": email, "password": pwd})
    t2 = l2.json()["access_token"]
    r2 = l2.json()["refresh_token"]

    # Both tokens work
    assert (await client.get("/auth/me", headers={"Authorization": f"Bearer {t1}"})).status_code == 200
    assert (await client.get("/auth/me", headers={"Authorization": f"Bearer {t2}"})).status_code == 200

    # Device 2 calls logout-all
    logout_all_res = await client.post(
        "/auth/logout-all",
        json={"current_refresh_token": r2, "keep_current": False},
        headers={"Authorization": f"Bearer {t2}"},
    )
    assert logout_all_res.status_code == 200

    # Both tokens are now rejected with 401
    assert (await client.get("/auth/me", headers={"Authorization": f"Bearer {t1}"})).status_code == 401
    assert (await client.get("/auth/me", headers={"Authorization": f"Bearer {t2}"})).status_code == 401


@pytest.mark.asyncio
async def test_access_token_validation_fails_open_on_redis_error(client: AsyncClient):
    """If Redis is down, get_current_user fails open rather than blocking all traffic."""
    email = "failopen@example.com"
    pwd = "Password123!"
    await client.post("/auth/register", json={"email": email, "password": pwd})
    login_res = await client.post("/auth/login", json={"email": email, "password": pwd})
    token = login_res.json()["access_token"]

    broken_redis = AsyncMock()
    broken_redis.get.side_effect = ConnectionError("Redis down")

    with patch("app.core.redis.RedisClient.get_client", new=AsyncMock(return_value=broken_redis)):
        res = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200  # Allowed through (fail-open)
