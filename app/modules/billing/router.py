"""
BILLING MODULE — router.py

Public, tenant-scoped, and platform-admin billing and entitlement endpoints.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_membership,
    get_current_user,
    require_platform_admin,
    require_roles,
)
from app.core.exceptions import ForbiddenError
from app.modules.auth.models import User
from app.modules.billing.schemas import (
    AdminPlanUpdate,
    EntitlementsResponse,
    PlanSchema,
    PlatformLimitsResponse,
    UpgradeRequestCreate,
    UpgradeRequestResponse,
)
from app.modules.billing.service import BillingService
from app.modules.memberships.models import MembershipRole
from app.modules.memberships.repository import MembershipRepository
from app.modules.organizations.schemas import OrganizationResponse

router = APIRouter(tags=["billing"])


@router.get("/plans", response_model=list[PlanSchema])
async def list_plans(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PlanSchema]:
    """Public listing of all available workspace plans, quotas, and features."""
    return await BillingService(db).get_plans()


@router.get("/platform/limits", response_model=PlatformLimitsResponse)
async def get_platform_limits() -> PlatformLimitsResponse:
    """Public details on infrastructure provider constraints, service status, and deployment facts."""
    return BillingService.get_platform_limits()


@router.get("/organizations/{org_id}/entitlements", response_model=EntitlementsResponse)
async def get_organization_entitlements(
    org_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EntitlementsResponse:
    """Real-time entitlements, limits, and usage statistics for an organization member."""
    membership = await MembershipRepository(db).get_by_user_and_org(
        user_id=current_user.id,
        organization_id=org_id,
    )
    if not membership:
        raise ForbiddenError("You are not a member of this organization")

    return await BillingService(db).get_entitlements(org_id)


@router.post(
    "/organizations/{org_id}/upgrade-request",
    response_model=UpgradeRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_plan_upgrade(
    org_id: UUID,
    data: UpgradeRequestCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UpgradeRequestResponse:
    """Submit a request to upgrade workspace plan. Requires OWNER or ADMIN role."""
    membership = await MembershipRepository(db).get_by_user_and_org(
        user_id=current_user.id,
        organization_id=org_id,
    )
    if not membership or membership.role not in (MembershipRole.OWNER, MembershipRole.ADMIN):
        raise ForbiddenError("Only owners and admins can request workspace upgrades")

    req = await BillingService(db).create_upgrade_request(
        organization_id=org_id,
        requested_by=current_user.id,
        data=data,
    )
    return UpgradeRequestResponse.model_validate(req)


@router.get("/admin/upgrade-requests", response_model=list[UpgradeRequestResponse])
async def list_admin_upgrade_requests(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_platform_admin)],
    status: str | None = Query(None, description="Filter by status (pending|approved|rejected)"),
) -> list[UpgradeRequestResponse]:
    """Platform admin endpoint to list and review pending tenant upgrade requests."""
    items = await BillingService(db).list_upgrade_requests(status=status)
    return [UpgradeRequestResponse.model_validate(item) for item in items]


@router.patch("/admin/organizations/{org_id}/plan", response_model=OrganizationResponse)
async def admin_change_organization_plan(
    org_id: UUID,
    data: AdminPlanUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_platform_admin)],
) -> OrganizationResponse:
    """Platform admin endpoint to execute an organization plan upgrade or downgrade."""
    org = await BillingService(db).update_organization_plan(
        organization_id=org_id,
        new_plan=data.plan,
        actor_user_id=current_user.id,
    )
    return OrganizationResponse.model_validate(org)

