"""
ORGANIZATIONS MODULE — router.py

  POST /organizations     — create tenant (JWT required)
  GET  /organizations/my  — list tenants you belong to (JWT required)

Org id from create response is used later as X-Organization-Id for /files.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.organizations.schemas import (
    OrganizationCreate,
    OrganizationDeleteConfirmation,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.modules.organizations.service import OrganizationService
from uuid import UUID

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OrganizationResponse:
    org = await OrganizationService(db).create_organization(current_user.id, data)
    return OrganizationResponse.model_validate(org)


@router.get("/my", response_model=list[OrganizationResponse])
async def list_my_organizations(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[OrganizationResponse]:
    return await OrganizationService(db).list_user_organizations(current_user.id)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OrganizationResponse:
    """G1: Get organization detail including caller's role and member_count."""
    return await OrganizationService(db).get_organization_detail(current_user.id, org_id)


@router.post("/{org_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_organization(
    org_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """G5: Leave organization for non-owner member. Owner must transfer first."""
    await OrganizationService(db).leave_organization(current_user.id, org_id)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: UUID,
    confirmation: OrganizationDeleteConfirmation,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """G6: Delete organization by owner with confirmation matching exact name."""
    await OrganizationService(db).delete_organization(
        user_id=current_user.id,
        organization_id=org_id,
        confirmed_name=confirmation.name,
    )


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def rename_organization(
    org_id: UUID,
    data: OrganizationUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OrganizationResponse:
    org = await OrganizationService(db).rename_organization(
        requester_user_id=current_user.id,
        organization_id=org_id,
        new_name=data.name,
    )
    return OrganizationResponse.model_validate(org)

