"""
Request context helpers.

Provides FastAPI dependencies and plain helpers to extract:
  - Client IP address (respects X-Forwarded-For proxy header)
  - User-Agent string

Inject into routes via Depends(get_request_info).
"""

from fastapi import Request
from app.core.config import get_settings


def get_client_ip(request: Request) -> str:
    """
    Return the real client IP.

    Behind Render or reverse proxies, the client IP is in X-Forwarded-For.
    We take the left-most entry when TRUSTED_PROXY_COUNT >= 1.
    Falls back to request.client.host or '127.0.0.1'.
    """
    settings = get_settings()
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for and settings.trusted_proxy_count > 0:
        ips = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
        if ips:
            return ips[0]
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


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
