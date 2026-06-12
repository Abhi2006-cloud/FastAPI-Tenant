"""
FastAPI dependencies: identity (JWT) and multi-tenant access control.

This is the main enforcement layer for multi-tenancy:
  1. get_current_user     — WHO is calling (from Authorization: Bearer)
  2. get_organization_id_header — WHICH tenant (from X-Organization-Id)
  3. get_current_membership — IS this user allowed in that tenant?
  4. require_roles        — DOES the user have owner/admin (etc.)?

Use these in routers via Depends(...); services also call MembershipService
for the same checks when org_id comes from the URL path instead of the header.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import get_token_subject
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.memberships.models import Membership, MembershipRole
from app.modules.memberships.repository import MembershipRepository

# auto_error=False lets us return 401 with a clear message instead of FastAPI default
security_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security_scheme)
    ],
) -> User:
    """
    Resolve JWT -> User row. Used on every protected endpoint.

    Client must send: Authorization: Bearer <access_token from /auth/login>
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError()

    try:
        user_id = get_token_subject(credentials.credentials)
    except JWTError as exc:
        raise UnauthorizedError() from exc

    user = await UserRepository(db).get_by_id(user_id)
    if user is None:
        raise UnauthorizedError()
    return user


async def get_organization_id_header(
    x_organization_id: Annotated[str | None, Header(alias="X-Organization-Id")] = None,
) -> UUID:
    """
    Read active tenant (organization) from header.

    Required for org-scoped routes like /files. Frontend (or Postman) sends
    the org id the user selected in their workspace switcher.
    """
    if not x_organization_id:
        raise ForbiddenError("X-Organization-Id header is required")
    try:
        return UUID(x_organization_id)
    except ValueError as exc:
        raise ForbiddenError("Invalid X-Organization-Id header") from exc


async def get_current_membership(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
) -> Membership:
    """
    Prove the user belongs to the organization in X-Organization-Id.

    Returns the membership row (includes role). Raises 403 if no row exists —
    that is how we block cross-tenant access.
    """
    membership = await MembershipRepository(db).get_by_user_and_org(
        user_id=current_user.id,
        organization_id=organization_id,
    )
    if membership is None:
        raise ForbiddenError("You are not a member of this organization")
    return membership


def require_roles(*roles: MembershipRole):
    """
    Factory for role-based checks (e.g. only owner/admin can invite).

    Usage in a route:
        membership: Annotated[Membership, Depends(require_roles(MembershipRole.OWNER))]
    """

    async def _checker(
        membership: Annotated[Membership, Depends(get_current_membership)],
    ) -> Membership:
        if membership.role not in roles:
            raise ForbiddenError("Insufficient permissions for this action")
        return membership

    return _checker
