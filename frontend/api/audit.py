"""Audit logs API client."""

from datetime import datetime
from typing import Any

from frontend.api.client import APIError, api_client


def list_audit_logs(
    page: int = 1,
    page_size: int = 20,
    action: str | None = None,
    actor_user_id: str | None = None,
    resource_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]:
    """List audit logs for the current organization."""
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if action:
        params["action"] = action
    if actor_user_id:
        params["actor_user_id"] = actor_user_id
    if resource_type:
        params["resource_type"] = resource_type
    if start_date:
        params["start_date"] = start_date.isoformat()
    if end_date:
        params["end_date"] = end_date.isoformat()

    try:
        return api_client.get("/audit-logs", params=params)
    except APIError as e:
        raise APIError(f"Failed to list audit logs: {e.message}", e.status_code)


def search_audit_logs(
    query: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Search audit logs for the current organization."""
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if query:
        params["q"] = query
    if action:
        params["action"] = action
    if resource_type:
        params["resource_type"] = resource_type

    try:
        return api_client.get("/audit-logs/search", params=params)
    except APIError as e:
        raise APIError(f"Failed to search audit logs: {e.message}", e.status_code)
