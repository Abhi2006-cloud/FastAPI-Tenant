import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_platform_limits_public(client: AsyncClient):
    """GET /platform/limits is public and returns deployment infrastructure facts."""
    response = await client.get("/platform/limits")
    assert response.status_code == 200
    data = response.json()

    assert data["deployment"]["storage_backend"] in ("postgres", "local")
    assert "worker_mode" in data["deployment"]
    assert data["compute_provider"]["memory_mb"] == 512
    assert "Neon" in data["database_provider"]["name"]
    assert data["redis_provider"]["max_commands_per_second"] == 10000
    assert "search" in data["services"]
    assert "email" in data["services"]
