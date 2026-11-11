import io
import uuid

import pytest
from httpx import AsyncClient


async def _auth_headers(client: AsyncClient, email: str) -> dict[str, str]:
    if "@" in email:
        name, domain = email.split("@")
        unique_email = f"{name}_{uuid.uuid4().hex[:6]}@{domain}"
    else:
        unique_email = f"{email}_{uuid.uuid4().hex[:6]}@example.com"

    await client.post(
        "/auth/register",
        json={"email": unique_email, "password": "securepass123"},
    )
    login = await client.post(
        "/auth/login",
        json={"email": unique_email, "password": "securepass123"},
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


@pytest.mark.asyncio
async def test_get_file_details(client: AsyncClient) -> None:
    headers = await _auth_headers(client, "user@example.com")
    org = (
        await client.post(
            "/organizations",
            json={"name": "Details Org"},
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
        files={"file": ("document.pdf", io.BytesIO(b"pdf content"), "application/pdf")},
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["id"]

    details_response = await client.get(f"/files/{file_id}", headers=tenant_headers)
    assert details_response.status_code == 200
    file_details = details_response.json()
    assert file_details["file_name"] == "document.pdf"
    assert file_details["file_size"] == 11
    assert "download_url" in file_details


@pytest.mark.asyncio
async def test_download_file(client: AsyncClient) -> None:
    headers = await _auth_headers(client, "downloader@example.com")
    org = (
        await client.post(
            "/organizations",
            json={"name": "Download Org"},
            headers=headers,
        )
    ).json()

    tenant_headers = {
        **headers,
        "X-Organization-Id": org["id"],
    }

    content = b"download test content"
    upload_response = await client.post(
        "/files/upload",
        headers=tenant_headers,
        files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["id"]

    download_response = await client.get(f"/files/{file_id}/download", headers=tenant_headers)
    assert download_response.status_code == 200
    assert download_response.content == content


@pytest.mark.asyncio
async def test_download_missing_file(client: AsyncClient) -> None:
    headers = await _auth_headers(client, "user@example.com")
    org = (
        await client.post(
            "/organizations",
            json={"name": "Missing Org"},
            headers=headers,
        )
    ).json()

    tenant_headers = {
        **headers,
        "X-Organization-Id": org["id"],
    }

    fake_file_id = "00000000-0000-0000-0000-000000000000"
    download_response = await client.get(f"/files/{fake_file_id}/download", headers=tenant_headers)
    assert download_response.status_code == 404


@pytest.mark.asyncio
async def test_cross_tenant_download_forbidden(client: AsyncClient) -> None:
    owner_headers = await _auth_headers(client, "owner@example.com")
    org = (
        await client.post(
            "/organizations",
            json={"name": "Cross Tenant Org"},
            headers=owner_headers,
        )
    ).json()

    tenant_headers = {
        **owner_headers,
        "X-Organization-Id": org["id"],
    }

    upload_response = await client.post(
        "/files/upload",
        headers=tenant_headers,
        files={"file": ("secret.txt", io.BytesIO(b"secret"), "text/plain")},
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["id"]

    outsider_headers = await _auth_headers(client, "outsider@example.com")
    outsider_org = (
        await client.post(
            "/organizations",
            json={"name": "Outsider Org"},
            headers=outsider_headers,
        )
    ).json()

    outsider_tenant_headers = {
        **outsider_headers,
        "X-Organization-Id": outsider_org["id"],
    }

    download_response = await client.get(f"/files/{file_id}/download", headers=outsider_tenant_headers)
    assert download_response.status_code == 403


@pytest.mark.asyncio
async def test_delete_file_as_owner(client: AsyncClient) -> None:
    headers = await _auth_headers(client, "owner@example.com")
    org = (
        await client.post(
            "/organizations",
            json={"name": "Delete Org"},
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
        files={"file": ("to_delete.txt", io.BytesIO(b"delete me"), "text/plain")},
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["id"]

    delete_response = await client.delete(f"/files/{file_id}", headers=tenant_headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "file deleted"

    # Verify file is deleted
    get_response = await client.get(f"/files/{file_id}", headers=tenant_headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_own_file_as_member(client: AsyncClient) -> None:
    headers = await _auth_headers(client, "member@example.com")
    org = (
        await client.post(
            "/organizations",
            json={"name": "Member Delete Org"},
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
        files={"file": ("my_file.txt", io.BytesIO(b"my content"), "text/plain")},
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["id"]

    delete_response = await client.delete(f"/files/{file_id}", headers=tenant_headers)
    assert delete_response.status_code == 200


from unittest.mock import patch

@pytest.mark.asyncio
async def test_delete_other_user_file_forbidden_as_member(client: AsyncClient) -> None:
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        owner_headers = await _auth_headers(client, "owner@example.com")
        org = (
            await client.post(
                "/organizations",
                json={"name": "RBAC Org"},
                headers=owner_headers,
            )
        ).json()

        owner_tenant_headers = {
            **owner_headers,
            "X-Organization-Id": org["id"],
        }

        # Owner uploads a file
        upload_response = await client.post(
            "/files/upload",
            headers=owner_tenant_headers,
            files={"file": ("owner_file.txt", io.BytesIO(b"owner content"), "text/plain")},
        )
        assert upload_response.status_code == 201
        file_id = upload_response.json()["id"]

        # Member tries to delete owner's file
        # Real invitation flow so member is a verified tenant member with role MEMBER
        member_email = f"member_{uuid.uuid4().hex[:6]}@example.com"
        await client.post(
            "/auth/register",
            json={"email": member_email, "password": "securepass123"},
        )
        login_res = await client.post(
            "/auth/login",
            json={"email": member_email, "password": "securepass123"},
        )
        member_token = login_res.json()["access_token"]
        member_headers = {"Authorization": f"Bearer {member_token}"}

        invite_res = await client.post(
            f"/organizations/{org['id']}/invite",
            json={"email": member_email},
            headers=owner_headers,
        )
        assert invite_res.status_code == 201
        invite_token = invite_res.json()["token"]

        accept_res = await client.post(
            "/invitations/accept",
            json={"token": invite_token},
            headers=member_headers,
        )
        assert accept_res.status_code == 200

        member_tenant_headers = {
            **member_headers,
            "X-Organization-Id": org["id"],
        }

        # Member attempts to delete owner's file -> 403 Forbidden specifically due to RBAC
        delete_response = await client.delete(f"/files/{file_id}", headers=member_tenant_headers)
        assert delete_response.status_code == 403
        assert "You can only delete files you uploaded" in delete_response.text

        # Member uploads their own file -> 201
        member_upload = await client.post(
            "/files/upload",
            headers=member_tenant_headers,
            files={"file": ("member_doc.txt", io.BytesIO(b"my own file"), "text/plain")},
        )
        assert member_upload.status_code == 201
        member_file_id = member_upload.json()["id"]

        # Member can delete their own file -> 200
        member_delete = await client.delete(f"/files/{member_file_id}", headers=member_tenant_headers)
        assert member_delete.status_code == 200


@pytest.mark.asyncio
async def test_delete_missing_file(client: AsyncClient) -> None:
    headers = await _auth_headers(client, "user@example.com")
    org = (
        await client.post(
            "/organizations",
            json={"name": "Missing Delete Org"},
            headers=headers,
        )
    ).json()

    tenant_headers = {
        **headers,
        "X-Organization-Id": org["id"],
    }

    fake_file_id = "00000000-0000-0000-0000-000000000000"
    delete_response = await client.delete(f"/files/{fake_file_id}", headers=tenant_headers)
    assert delete_response.status_code == 404


@pytest.mark.asyncio
async def test_get_file_statistics(client: AsyncClient) -> None:
    headers = await _auth_headers(client, "stats@example.com")
    org = (
        await client.post(
            "/organizations",
            json={"name": "Stats Org"},
            headers=headers,
        )
    ).json()

    tenant_headers = {
        **headers,
        "X-Organization-Id": org["id"],
    }

    # Upload multiple files
    await client.post(
        "/files/upload",
        headers=tenant_headers,
        files={"file": ("file1.txt", io.BytesIO(b"a" * 100), "text/plain")},
    )
    await client.post(
        "/files/upload",
        headers=tenant_headers,
        files={"file": ("file2.txt", io.BytesIO(b"b" * 200), "text/plain")},
    )

    stats_response = await client.get("/files/stats", headers=tenant_headers)
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["total_files"] == 2
    assert stats["total_size_bytes"] == 300
    assert stats["average_file_size"] == 150


def test_storage_path_containment_and_traversal_protection(tmp_path) -> None:
    """Verify that StorageService strictly enforces canonical path containment."""
    from pathlib import Path
    from app.core.exceptions import ForbiddenError
    from app.modules.files.storage import StorageService

    storage_root = tmp_path / "storage_root"
    storage_root.mkdir()
    storage = StorageService(storage_root)

    # 1. Valid path inside storage root
    valid_file = storage_root / "org1" / "file.txt"
    storage.save(valid_file, b"valid content")
    assert storage.exists(valid_file)
    assert storage.read(valid_file) == b"valid content"
    assert storage.get_file_size(valid_file) == 13
    assert storage.delete(valid_file) is True

    # 2. Path traversal with ../
    traversal_path = storage_root / "org1" / ".." / ".." / "outside.txt"
    with pytest.raises(ForbiddenError, match="Path traversal detected"):
        storage.save(traversal_path, b"evil")

    with pytest.raises(ForbiddenError, match="Path traversal detected"):
        storage.read(traversal_path)

    with pytest.raises(ForbiddenError, match="Path traversal detected"):
        storage.delete(traversal_path)

    # 3. Absolute path outside storage root
    outside_file = tmp_path / "secret.txt"
    outside_file.write_bytes(b"sensitive")
    with pytest.raises(ForbiddenError, match="Path traversal detected"):
        storage.read(outside_file)

    # 4. Symlink escape attempt
    link_path = storage_root / "symlink_escape"
    try:
        link_path.symlink_to(outside_file)
        with pytest.raises(ForbiddenError, match="Path traversal detected"):
            storage.read(link_path)
    except OSError:
        pass  # If OS does not permit symlink creation in test environment


@pytest.mark.asyncio
async def test_upload_size_limit_rejection_and_cleanup(client: AsyncClient, monkeypatch) -> None:
    """Verify that files exceeding the size limit are aborted and partial files cleaned up."""
    from app.core.config import get_settings

    headers = await _auth_headers(client, "sizetest@example.com")
    org = (
        await client.post(
            "/organizations",
            json={"name": "Size Limit Org"},
            headers=headers,
        )
    ).json()

    tenant_headers = {
        **headers,
        "X-Organization-Id": org["id"],
    }

    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "max_upload_size_mb", 1)

    # Attempt to upload 1.5 MB file
    oversized_data = b"x" * (1024 * 1024 + 500)
    upload_res = await client.post(
        "/files/upload",
        headers=tenant_headers,
        files={"file": ("large.txt", io.BytesIO(oversized_data), "text/plain")},
    )
    assert upload_res.status_code == 400
    assert "File exceeds maximum size" in upload_res.text

    # Verify no file remains in the organization upload folder
    import os
    org_folder = os.path.join(settings.upload_dir, org["id"])
    if os.path.exists(org_folder):
        files_in_folder = os.listdir(org_folder)
        assert len(files_in_folder) == 0

    # Attempt to upload empty file -> 400
    empty_res = await client.post(
        "/files/upload",
        headers=tenant_headers,
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert empty_res.status_code == 400
    assert "Empty file" in empty_res.text
