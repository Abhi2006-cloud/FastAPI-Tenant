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

import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.redis import RedisClient
from app.core.security import decode_access_token, get_token_subject
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.memberships.models import Membership, MembershipRole
from app.modules.memberships.repository import MembershipRepository

logger = logging.getLogger(__name__)

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
        payload = decode_access_token(credentials.credentials)
    except (JWTError, ValueError) as exc:
        raise UnauthorizedError() from exc

    # Check session revocation via Redis blacklist (fail-open on Redis errors)
    sid = payload.get("sid")
    if sid:
        try:
            client = await RedisClient.get_client()
            is_revoked = await client.get(f"revoked_session:{sid}")
            if is_revoked:
                raise UnauthorizedError("Session has been revoked")
        except UnauthorizedError:
            raise
        except Exception as exc:
            logger.warning("Redis session revocation check failed (failing open): %s", exc)

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


async def require_platform_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency ensuring caller email is in PLATFORM_ADMIN_EMAILS list."""
    settings = get_settings()
    if current_user.email.lower() not in settings.platform_admin_email_list:
        raise ForbiddenError("Platform administrator privilege required")
    return current_user


def require_feature(feature_key: str):
    """
    Dependency ensuring the active organization's plan includes and enables the requested feature.
    Returns HTTP 402 PLAN_FEATURE_LOCKED if plan level is insufficient or deployment disabled.
    """
    async def _checker(
        db: DbSession,
        organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    ) -> None:
        from app.modules.billing.plans import ALL_FEATURES, evaluate_feature_state
        from app.modules.organizations.repository import OrganizationRepository

        org = await OrganizationRepository(db).get_by_id(organization_id)
        if not org:
            raise ForbiddenError("Organization not found")

        feat = next((f for f in ALL_FEATURES if f.key == feature_key), None)
        if not feat:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown feature key: {feature_key}",
            )

        state = evaluate_feature_state(feat, org.plan or "free")
        if state != "included":
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "PLAN_FEATURE_LOCKED",
                    "feature": feature_key,
                    "state": state,
                    "required_plan": feat.min_plan,
                    "current_plan": org.plan or "free",
                },
            )

    return _checker

