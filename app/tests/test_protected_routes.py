import io

import pytest
from httpx import AsyncClient


async def _auth_headers(client: AsyncClient, email: str) -> dict[str, str]:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "securepass123"},
    )
    login = await client.post(
        "/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_files_require_organization_header(client: AsyncClient) -> None:
    headers = await _auth_headers(client, "filesuser@example.com")

    response = await client.get("/files", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_isolation_for_files(client: AsyncClient) -> None:
    owner_headers = await _auth_headers(client, "owner@example.com")
    org = (
        await client.post(
            "/organizations",
            json={"name": "Tenant Org"},
            headers=owner_headers,
        )
    ).json()

    outsider_headers = await _auth_headers(client, "outsider@example.com")

    response = await client.get(
        "/files",
        headers={
            **outsider_headers,
            "X-Organization-Id": org["id"],
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_upload_and_list_files(client: AsyncClient) -> None:
    headers = await _auth_headers(client, "uploader@example.com")
    org = (
        await client.post(
            "/organizations",
            json={"name": "Files Org"},
            headers=headers,
        )
    ).json()

    tenant_headers = {
        **headers,
        "X-Organization-Id": org["id"],
    }

    upload_response = await client.post(
        "/files/upload",
        headers=tenant_headers,
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert upload_response.status_code == 201

    list_response = await client.get("/files", headers=tenant_headers)
    assert list_response.status_code == 200
    files = list_response.json()
    assert len(files) == 1
    assert files[0]["file_name"] == "notes.txt"
