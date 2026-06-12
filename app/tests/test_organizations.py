import pytest
from httpx import AsyncClient


async def _register_and_token(client: AsyncClient, email: str) -> str:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "securepass123"},
    )
    login = await client.post(
        "/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_create_and_list_organizations(client: AsyncClient) -> None:
    token = await _register_and_token(client, "orgowner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/organizations",
        json={"name": "Acme Workspace"},
        headers=headers,
    )
    assert create_response.status_code == 201
    org = create_response.json()
    assert org["name"] == "Acme Workspace"

    list_response = await client.get("/organizations/my", headers=headers)
    assert list_response.status_code == 200
    orgs = list_response.json()
    assert len(orgs) == 1
    assert orgs[0]["id"] == org["id"]
