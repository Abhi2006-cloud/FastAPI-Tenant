"""Health check API client."""

from frontend.api.client import api_client


def get_health() -> dict:
    """Get application health status."""
    return api_client.get("/health", require_auth=False)
