"""Files API client."""

from typing import Any

from frontend.api.client import api_client, APIError


def upload_file(file) -> dict:
    """Upload a file to the current organization."""
    try:
        files = {"file": (file.name, file, file.type)}
        response = api_client.post(
            "/files/upload",
            files=files
        )
        return response
    except APIError as e:
        raise APIError(f"Failed to upload file: {e.message}", e.status_code)


def list_files() -> list:
    """List files in the current organization."""
    try:
        response = api_client.get("/files")
        return response
    except APIError as e:
        raise APIError(f"Failed to list files: {e.message}", e.status_code)


def get_file_details(file_id: str) -> dict[str, Any]:
    """Get details for a specific file."""
    try:
        response = api_client.get(f"/files/{file_id}")
        return response
    except APIError as e:
        raise APIError(f"Failed to get file details: {e.message}", e.status_code)


def download_file(file_id: str) -> bytes:
    """Download a file by ID."""
    try:
        response = api_client.get(f"/files/{file_id}/download")
        return response
    except APIError as e:
        raise APIError(f"Failed to download file: {e.message}", e.status_code)


def delete_file(file_id: str) -> dict[str, Any]:
    """Delete a file by ID."""
    try:
        response = api_client.delete(f"/files/{file_id}")
        return response
    except APIError as e:
        raise APIError(f"Failed to delete file: {e.message}", e.status_code)


def get_file_statistics() -> dict[str, Any]:
    """Get file statistics for the current organization."""
    try:
        response = api_client.get("/files/stats")
        return response
    except APIError as e:
        raise APIError(f"Failed to get file statistics: {e.message}", e.status_code)
