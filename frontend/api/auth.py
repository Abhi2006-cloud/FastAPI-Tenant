"""Authentication API client."""

from frontend.api.client import api_client, APIError


def register(email: str, password: str) -> dict:
    """Register a new user."""
    try:
        response = api_client.post(
            "/auth/register",
            data={"email": email, "password": password},
            require_auth=False
        )
        return response
    except APIError as e:
        raise APIError(f"Registration failed: {e.message}", e.status_code)


def login(email: str, password: str) -> dict:
    """Login and get access token."""
    try:
        response = api_client.post(
            "/auth/login",
            data={"email": email, "password": password},
            require_auth=False
        )
        return response
    except APIError as e:
        raise APIError(f"Login failed: {e.message}", e.status_code)


def get_me() -> dict:
    """Get current user information."""
    try:
        response = api_client.get("/auth/me")
        return response
    except APIError as e:
        raise APIError(f"Failed to get user info: {e.message}", e.status_code)
