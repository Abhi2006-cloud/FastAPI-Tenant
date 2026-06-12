"""
Tenant context middleware (optional helper for V1).

Reads X-Organization-Id and stores it in a ContextVar for the duration of the request.

NOTE: Real tenant enforcement happens in app/core/dependencies.py (get_current_membership).
Nothing in V1 requires this middleware; it is scaffolding for logging, auditing,
or services that cannot use FastAPI Depends() easily in future versions.
"""

from contextvars import ContextVar
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

tenant_organization_id: ContextVar[UUID | None] = ContextVar(
    "tenant_organization_id", default=None
)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Stores the active organization id from the request header for downstream use."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        org_header = request.headers.get("X-Organization-Id")
        token = tenant_organization_id.set(None)
        if org_header:
            try:
                tenant_organization_id.set(UUID(org_header))
            except ValueError:
                tenant_organization_id.set(None)

        try:
            return await call_next(request)
        finally:
            tenant_organization_id.reset(token)


def get_tenant_organization_id() -> UUID | None:
    """Read active org id anywhere in the same async request (if middleware ran)."""
    return tenant_organization_id.get()
