"""Unit tests for PostgreSQL BYTEA blob storage backend.

Verifies:
- Upload creates FileRecord with pg:// path and persists FileBlob row.
- Download streams correct binary content from file_blobs.
- Delete removes both file_blobs and metadata.
- Cross-tenant isolation (403/404).
- Size limit enforcement (MAX_UPLOAD_SIZE_MB).
"""

import io
from uuid import UUID
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.modules.files.blob_model import FileBlob
from app.modules.files.models import FileRecord
from app.tests.test_audit_logs import _register_and_token


@pytest.mark.asyncio
async def test_postgres_storage_upload_download_delete_cycle(client: AsyncClient, db_engine):
    settings = get_settings()
    settings.storage_backend = "postgres"

    token_a = await _register_and_token(client, "user_pg_a@example.com")
    org_res = await client.post(
        "/organizations",
        json={"name": "Org Postgres A"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert org_res.status_code == 201
    org_id = org_res.json()["id"]

    headers_a = {
        "Authorization": f"Bearer {token_a}",
        "X-Organization-Id": org_id,
    }

    # 1. Upload
    content = b"Important binary database blob data"
    file_payload = {"file": ("blob.txt", io.BytesIO(content), "text/plain")}
    upload_res = await client.post("/files/upload", headers=headers_a, files=file_payload)
    assert upload_res.status_code == 201
    data = upload_res.json()
    file_id = data["id"]
    file_path = data["file_path"]

    # Verify pseudo-path format
    assert file_path.startswith("pg://")
    assert str(org_id) in file_path
    assert str(file_id) in file_path

    # Verify database blob row exists
    from app.core.database import async_session_factory
    async with async_session_factory() as session:
        blob_result = await session.execute(
            select(FileBlob).where(FileBlob.file_id == UUID(file_id))
        )
        blob = blob_result.scalar_one_or_none()
        assert blob is not None
        assert blob.content == content

    # 2. Download
    download_res = await client.get(f"/files/{file_id}/download", headers=headers_a)
    assert download_res.status_code == 200
    assert download_res.content == content
    assert "blob.txt" in download_res.headers.get("content-disposition", "")

    # 3. Cross-tenant isolation (Tenant B cannot access or download)
    token_b = await _register_and_token(client, "user_pg_b@example.com")
    org_b_res = await client.post(
        "/organizations",
        json={"name": "Org Postgres B"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    org_b_id = org_b_res.json()["id"]
    headers_b = {
        "Authorization": f"Bearer {token_b}",
        "X-Organization-Id": org_b_id,
    }

    cross_get = await client.get(f"/files/{file_id}", headers=headers_b)
    assert cross_get.status_code in (403, 404)

    cross_download = await client.get(f"/files/{file_id}/download", headers=headers_b)
    assert cross_download.status_code in (403, 404)

    # 4. Delete
    delete_res = await client.delete(f"/files/{file_id}", headers=headers_a)
    assert delete_res.status_code == 200

    # Verify blob and record removed from database
    async with async_session_factory() as session:
        blob_check = await session.execute(
            select(FileBlob).where(FileBlob.file_id == UUID(file_id))
        )
        assert blob_check.scalar_one_or_none() is None

        file_check = await session.execute(
            select(FileRecord).where(FileRecord.id == UUID(file_id))
        )
        assert file_check.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_postgres_storage_size_limit_rejection(client: AsyncClient, db_engine):
    settings = get_settings()
    settings.storage_backend = "postgres"
    settings.max_upload_size_mb = 2  # Free tier default limit 2 MB

    token = await _register_and_token(client, "user_limit@example.com")
    org_res = await client.post(
        "/organizations",
        json={"name": "Org Limit Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = org_res.json()["id"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": org_id,
    }

    # Oversized payload: 2 MB + 1024 bytes
    oversized_content = b"x" * (2 * 1024 * 1024 + 1024)
    file_payload = {"file": ("big.txt", io.BytesIO(oversized_content), "text/plain")}

    res = await client.post("/files/upload", headers=headers, files=file_payload)
    # In Phase 2, plan limit enforcement returns 402 PLAN_LIMIT_REACHED
    assert res.status_code in (400, 402)
    detail_str = str(res.json().get("detail", "")).lower()
    assert "maximum" in detail_str or "plan_limit_reached" in detail_str
