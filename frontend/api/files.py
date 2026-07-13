"""Files API client."""

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
