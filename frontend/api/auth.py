"""Authentication API client — v2.4.0 with session management."""

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
    """Login and get access + refresh tokens + session_id."""
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


def refresh_token(current_refresh_token: str) -> dict:
    """
    Rotate refresh token and get a new access token.

    Returns dict with access_token, refresh_token, session_id.
    """
    try:
        response = api_client.post(
            "/auth/refresh",
            data={"refresh_token": current_refresh_token},
            require_auth=False,
        )
        return response
    except APIError as e:
        raise APIError(f"Token refresh failed: {e.message}", e.status_code)


def logout(current_refresh_token: str) -> None:
    """Revoke the current session by invalidating the refresh token."""
    try:
        api_client.post(
            "/auth/logout",
            data={"refresh_token": current_refresh_token},
            require_auth=False,
        )
    except APIError:
        pass  # Ignore errors on logout — session may already be expired


def logout_all(current_refresh_token: str | None = None, keep_current: bool = True) -> dict:
    """Revoke all sessions. Returns {"revoked": count}."""
    try:
        payload: dict = {"keep_current": keep_current}
        if current_refresh_token:
            payload["refresh_token"] = current_refresh_token
        response = api_client.post("/auth/logout-all", data=payload)
        return response
    except APIError as e:
        raise APIError(f"Logout all failed: {e.message}", e.status_code)


def get_sessions(current_session_id: str | None = None) -> dict:
    """
    Get all active sessions for the current user.

    Returns dict with 'sessions' list and 'total' count.
    """
    try:
        params = {}
        if current_session_id:
            params["current_session_id"] = current_session_id
        response = api_client.get("/auth/sessions", params=params)
        return response
    except APIError as e:
        raise APIError(f"Failed to get sessions: {e.message}", e.status_code)


def revoke_session(session_id: str) -> None:
    """Remotely revoke a specific session by ID."""
    try:
        api_client.delete(f"/auth/sessions/{session_id}")
    except APIError as e:
        raise APIError(f"Failed to revoke session: {e.message}", e.status_code)
