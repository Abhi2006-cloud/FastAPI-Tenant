import io
import pytest
from httpx import AsyncClient
from unittest.mock import patch

from app.core.config import get_settings


async def _register_and_login(client: AsyncClient, email: str, password: str = "Password123!") -> str:
    res = await client.post("/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201
    res_login = await client.post("/auth/login", json={"email": email, "password": password})
    assert res_login.status_code == 200
    return res_login.json()["access_token"]


async def _create_org(client: AsyncClient, token: str, name: str) -> str:
    res = await client.post(
        "/organizations",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    return res.json()["id"]


@pytest.mark.asyncio
async def test_search_basic_validation_empty_query_422(client: AsyncClient):
    """GET /search/basic returns 422 when q is empty or omitted."""
    token = await _register_and_login(client, "search_user_val@example.com")
    org_id = await _create_org(client, token, "Val Org")
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # Missing query param
    res_missing = await client.get("/search/basic", headers=headers)
    assert res_missing.status_code == 422

    # Empty string query param
    res_empty = await client.get("/search/basic?q=", headers=headers)
    assert res_empty.status_code == 422


@pytest.mark.asyncio
async def test_search_basic_tenant_isolation_and_matching(client: AsyncClient):
    """GET /search/basic searches files, members, and audit logs with tenant isolation and case-insensitivity."""
    settings = get_settings()
    # Explicitly ensure SEARCH_ENABLED is false to prove it works without Meilisearch
    with patch.object(settings, "search_enabled", False):
        token_a = await _register_and_login(client, "alice_search@tenant-a.com")
        org_a = await _create_org(client, token_a, "Tenant Alpha")
        headers_a = {"Authorization": f"Bearer {token_a}", "X-Organization-Id": org_a}

        token_b = await _register_and_login(client, "bob_search@tenant-b.com")
        org_b = await _create_org(client, token_b, "Tenant Beta")
        headers_b = {"Authorization": f"Bearer {token_b}", "X-Organization-Id": org_b}

        # Upload a file in Tenant A
        file_content = b"Financial report Q4 content"
        res_upload = await client.post(
            "/files/upload",
            files={"file": ("Quarterly_Report_2026.pdf", io.BytesIO(file_content), "application/pdf")},
            headers=headers_a,
        )
        assert res_upload.status_code == 201

        # Search in Tenant A for 'report' (case-insensitive)
        res_search_a = await client.get("/search/basic?q=report", headers=headers_a)
        assert res_search_a.status_code == 200
        data_a = res_search_a.json()
        assert data_a["query"] == "report"
        assert data_a["organization_id"] == org_a
        assert len(data_a["files"]) == 1
        assert "Quarterly_Report_2026.pdf" in data_a["files"][0]["file_name"]
        assert data_a["totals"]["files"] >= 1

        # Search in Tenant B for 'report' -> Tenant A's file must NOT appear
        res_search_b = await client.get("/search/basic?q=report", headers=headers_b)
        assert res_search_b.status_code == 200
        data_b = res_search_b.json()
        assert len(data_b["files"]) == 0
        assert data_b["totals"]["files"] == 0

        # Search member by email substring
        res_member_a = await client.get("/search/basic?q=ALICE", headers=headers_a)
        assert res_member_a.status_code == 200
        assert len(res_member_a.json()["members"]) == 1
        assert res_member_a.json()["members"][0]["email"] == "alice_search@tenant-a.com"

        # Search audit logs by action or resource
        res_audit_a = await client.get("/search/basic?q=organization", headers=headers_a)
        assert res_audit_a.status_code == 200
        assert len(res_audit_a.json()["audit_logs"]) >= 1


@pytest.mark.asyncio
async def test_search_basic_pagination(client: AsyncClient):
    """GET /search/basic correctly applies limit and offset to result sets."""
    token = await _register_and_login(client, "page_search@example.com")
    org_id = await _create_org(client, token, "Pagination Org")
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # Upload multiple files
    for i in range(3):
        await client.post(
            "/files/upload",
            files={"file": (f"doc_page_{i}.txt", io.BytesIO(b"data"), "text/plain")},
            headers=headers,
        )

    # Limit = 2, offset = 0
    res_p1 = await client.get("/search/basic?q=doc_page&limit=2&offset=0", headers=headers)
    assert res_p1.status_code == 200
    p1_data = res_p1.json()
    assert len(p1_data["files"]) == 2
    assert p1_data["totals"]["files"] == 3

    # Limit = 2, offset = 2
    res_p2 = await client.get("/search/basic?q=doc_page&limit=2&offset=2", headers=headers)
    assert res_p2.status_code == 200
    p2_data = res_p2.json()
    assert len(p2_data["files"]) == 1
    assert p2_data["totals"]["files"] == 3
    assert p1_data["files"][0]["id"] != p2_data["files"][0]["id"]
