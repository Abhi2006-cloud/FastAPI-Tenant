"""Auth tests — updated for v2.4.0 (access + refresh token response)."""

import pytest
from httpx import AsyncClient

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient) -> None:
    register_response = await client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "securepass123"},
    )
    assert register_response.status_code == 201
    body = register_response.json()
    assert body["email"] == "alice@example.com"
    assert "id" in body

    login_response = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "securepass123"},
    )
    assert login_response.status_code == 200
    token_body = login_response.json()
    assert token_body["token_type"] == "bearer"
    assert token_body["access_token"]
    # v2.4.0: refresh token and session_id must be present
    assert token_body["refresh_token"]
    assert token_body["session_id"]
    # expires_in should match ACCESS_TOKEN_EXPIRE_MINUTES * 60
    settings = get_settings()
    assert token_body["expires_in"] == settings.access_token_expire_minutes * 60


@pytest.mark.asyncio
async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user(client: AsyncClient) -> None:
    await client.post(
        "/auth/register",
        json={"email": "bob@example.com", "password": "securepass123"},
    )
    login_response = await client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "securepass123"},
    )
    token = login_response.json()["access_token"]

    me_response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "bob@example.com"
