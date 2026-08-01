"""Search API client."""

from typing import Any, Dict, Optional
from frontend.api.client import api_client

def global_search(query: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
    """Perform a global search across all organization data."""
    params = {"q": query, "limit": limit, "offset": offset}
    return api_client.get("/search", params=params, require_auth=True)

def search_organizations(query: str, limit: int = 10, offset: int = 0, sort: Optional[str] = None) -> Dict[str, Any]:
    """Search organization details."""
    params = {"q": query, "limit": limit, "offset": offset}
    if sort:
        params["sort"] = sort
    return api_client.get("/search/organizations", params=params, require_auth=True)

def search_members(query: str, limit: int = 10, offset: int = 0, sort: Optional[str] = None) -> Dict[str, Any]:
    """Search organization members."""
    params = {"q": query, "limit": limit, "offset": offset}
    if sort:
        params["sort"] = sort
    return api_client.get("/search/members", params=params, require_auth=True)

def search_files(query: str, limit: int = 10, offset: int = 0, sort: Optional[str] = None) -> Dict[str, Any]:
    """Search organization files."""
    params = {"q": query, "limit": limit, "offset": offset}
    if sort:
        params["sort"] = sort
    return api_client.get("/search/files", params=params, require_auth=True)

def search_audit_logs(query: str, limit: int = 10, offset: int = 0, sort: Optional[str] = None) -> Dict[str, Any]:
    """Search organization audit logs."""
    params = {"q": query, "limit": limit, "offset": offset}
    if sort:
        params["sort"] = sort
    return api_client.get("/search/audit_logs", params=params, require_auth=True)
