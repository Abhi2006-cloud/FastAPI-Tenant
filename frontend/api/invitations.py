"""Invitations API client."""

from frontend.api.client import api_client, APIError


def create_invitation(org_id: str, email: str) -> dict:
    """Create an invitation for an organization."""
    try:
        response = api_client.post(
            f"/organizations/{org_id}/invite",
            data={"email": email}
        )
        return response
    except APIError as e:
        raise APIError(f"Failed to create invitation: {e.message}", e.status_code)


def accept_invitation(token: str) -> dict:
    """Accept an invitation using token."""
    try:
        response = api_client.post(
            "/invitations/accept",
            data={"token": token}
        )
        return response
    except APIError as e:
        raise APIError(f"Failed to accept invitation: {e.message}", e.status_code)
