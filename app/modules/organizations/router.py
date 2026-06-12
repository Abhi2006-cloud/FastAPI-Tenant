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
from app.modules.organizations.schemas import OrganizationCreate, OrganizationResponse
from app.modules.organizations.service import OrganizationService

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
    orgs = await OrganizationService(db).list_user_organizations(current_user.id)
    return [OrganizationResponse.model_validate(org) for org in orgs]
