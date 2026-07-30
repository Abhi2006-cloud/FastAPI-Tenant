"""Health check API client."""

from frontend.api.client import api_call


def get_health() -> dict:
    """Get application health status."""
    return api_call("GET", "/health")
