"""
Request context helpers.

Provides FastAPI dependencies and plain helpers to extract:
  - Client IP address (respects X-Forwarded-For proxy header)
  - User-Agent string

Inject into routes via Depends(get_request_info).
"""

from fastapi import Request


def get_client_ip(request: Request) -> str | None:
    """
    Return the real client IP.

    Prefers X-Forwarded-For (set by reverse proxies / load balancers).
    Falls back to request.client.host for direct connections.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Header may be a comma-separated list; first entry is the real client
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def get_user_agent(request: Request) -> str | None:
    """Return raw User-Agent string from the request headers."""
    return request.headers.get("User-Agent")


class RequestInfo:
    """Parsed request metadata: IP address and User-Agent string."""

    __slots__ = ("ip_address", "user_agent")

    def __init__(self, ip_address: str | None, user_agent: str | None) -> None:
        self.ip_address = ip_address
        self.user_agent = user_agent


async def get_request_info(request: Request) -> RequestInfo:
    """
    FastAPI dependency: yields IP + User-Agent for the current request.

    Usage in a route:
        info: Annotated[RequestInfo, Depends(get_request_info)]
    """
    return RequestInfo(
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
