import time
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.redis import RedisClient


@pytest.mark.asyncio
async def test_rate_limit_login_burst_and_headers(client: AsyncClient):
    """POST /auth/login is rate limited to 10/min/IP."""
    email = "ratelimit_user@example.com"
    pwd = "Password123!"
    await client.post("/auth/register", json={"email": email, "password": pwd})

    fixed_time = 1700000010.0
    with patch("app.core.rate_limit.time.time", return_value=fixed_time):
        # First 10 requests allowed
        for i in range(10):
            res = await client.post(
                "/auth/login",
                json={"email": email, "password": pwd},
                headers={"X-Forwarded-For": "203.0.113.1"},
            )
            assert res.status_code == 200
            assert "X-RateLimit-Limit" in res.headers
            assert res.headers["X-RateLimit-Limit"] == "10"
            assert int(res.headers["X-RateLimit-Remaining"]) >= 0

        # 11th request: 429 RATE_LIMITED
        res_limited = await client.post(
            "/auth/login",
            json={"email": email, "password": pwd},
            headers={"X-Forwarded-For": "203.0.113.1"},
        )
        assert res_limited.status_code == 429
        assert res_limited.headers["X-RateLimit-Remaining"] == "0"
        assert "Retry-After" in res_limited.headers
        assert res_limited.headers["X-RateLimit-Limit"] == "10"
        body = res_limited.json()
        err = body.get("detail", body)
        assert err["code"] == "RATE_LIMITED"
        assert err["retry_after"] > 0


@pytest.mark.asyncio
async def test_rate_limit_per_ip_isolation(client: AsyncClient):
    """Different client IPs have isolated rate limit buckets."""
    fixed_time = 1700000010.0
    with patch("app.core.rate_limit.time.time", return_value=fixed_time):
        # Exhaust IP 1
        for _ in range(10):
            await client.post(
                "/auth/login",
                json={"email": "fake@example.com", "password": "wrong"},
                headers={"X-Forwarded-For": "198.51.100.5"},
            )

        res_ip1 = await client.post(
            "/auth/login",
            json={"email": "fake@example.com", "password": "wrong"},
            headers={"X-Forwarded-For": "198.51.100.5"},
        )
        assert res_ip1.status_code == 429

        # IP 2 should NOT be blocked
        res_ip2 = await client.post(
            "/auth/login",
            json={"email": "fake@example.com", "password": "wrong"},
            headers={"X-Forwarded-For": "198.51.100.6"},
        )
        assert res_ip2.status_code == 401  # Not 429!


@pytest.mark.asyncio
async def test_rate_limit_fail_open_on_redis_error(client: AsyncClient):
    """If Redis raises an exception, the rate limiter fails OPEN and allows the request."""
    broken_redis = AsyncMock()
    broken_redis.pipeline.side_effect = RuntimeError("Redis connection dropped")

    with patch("app.core.redis.RedisClient.get_client", new=AsyncMock(return_value=broken_redis)):
        res = await client.post(
            "/auth/login",
            json={"email": "fake@example.com", "password": "wrong"},
            headers={"X-Forwarded-For": "192.0.2.99"},
        )
        assert res.status_code == 401  # Allowed through to auth logic (fail-open)
