"""Organizations API client."""

from frontend.api.client import api_client, APIError


def create_organization(name: str) -> dict:
    """Create a new organization."""
    try:
        response = api_client.post(
            "/organizations",
            data={"name": name}
        )
        return response
    except APIError as e:
        raise APIError(f"Failed to create organization: {e.message}", e.status_code)


def list_my_organizations() -> list:
    """Get list of user's organizations."""
    try:
        response = api_client.get("/organizations/my")
        return response
    except APIError as e:
        raise APIError(f"Failed to list organizations: {e.message}", e.status_code)
