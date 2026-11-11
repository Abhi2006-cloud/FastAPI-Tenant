import pytest
from unittest.mock import MagicMock
from httpx import AsyncClient

from app.core.config import get_settings
from app.core.request_context import get_client_ip


def test_get_client_ip_with_trusted_proxy_count():
    # 1. Single proxy: client IP appended at the end
    req = MagicMock()
    req.headers = {"X-Forwarded-For": "198.51.100.1, 203.0.113.50"}
    req.client = MagicMock(host="10.0.0.1")
    assert get_client_ip(req) == "203.0.113.50"

    # Spoofed extra header prepended does not alter the extracted client IP
    req.headers = {"X-Forwarded-For": "10.0.0.99, 172.16.0.1, 198.51.100.1, 203.0.113.50"}
    assert get_client_ip(req) == "203.0.113.50"

    # Single IP in header
    req.headers = {"X-Forwarded-For": "203.0.113.50"}
    assert get_client_ip(req) == "203.0.113.50"

    # No header: direct client host is used
    req.headers = {}
    req.client = MagicMock(host="192.168.1.100")
    assert get_client_ip(req) == "192.168.1.100"

    # No header and no client host: fallback to 127.0.0.1
    req.client = None
    assert get_client_ip(req) == "127.0.0.1"


@pytest.mark.asyncio
async def test_proxy_ip_rate_limiting_buckets(client: AsyncClient):
    """Verify that different client IPs get separate rate limit buckets and spoofing doesn't evade limits."""
    email = "proxy_test@example.com"
    pwd = "Password123!"
    await client.post("/auth/register", json={"email": email, "password": pwd})

    headers_ip1 = {"X-Forwarded-For": "spoofed.ip.1, 203.0.113.10"}
    headers_ip1_spoofed = {"X-Forwarded-For": "another.spoof.2, yet.another.3, 203.0.113.10"}
    headers_ip2 = {"X-Forwarded-For": "spoofed.ip.1, 203.0.113.20"}

    # IP 1 makes calls with various spoofed headers; they should share the same bucket (203.0.113.10)
    res1 = await client.post(
        "/auth/login",
        json={"email": email, "password": pwd},
        headers=headers_ip1,
    )
    assert res1.status_code == 200
    rem1 = int(res1.headers["X-RateLimit-Remaining"])

    res2 = await client.post(
        "/auth/login",
        json={"email": email, "password": pwd},
        headers=headers_ip1_spoofed,
    )
    assert res2.status_code == 200
    rem2 = int(res2.headers["X-RateLimit-Remaining"])
    # The remaining counter must have decremented for the same real IP
    assert rem2 < rem1

    # Client IP 2 has its own separate bucket
    res3 = await client.post(
        "/auth/login",
        json={"email": email, "password": pwd},
        headers=headers_ip2,
    )
    assert res3.status_code == 200
    rem3 = int(res3.headers["X-RateLimit-Remaining"])
    # IP 2 starts from its own bucket (rem3 should be >= rem2)
    assert rem3 >= rem2
