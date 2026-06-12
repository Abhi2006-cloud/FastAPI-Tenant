"""
INVITATIONS MODULE — router.py

  POST /organizations/{org_id}/invite  — JWT; org_id in path (service checks membership)
  POST /invitations/accept             — JWT; body.token from invite response
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.invitations.schemas import (
    InvitationAccept,
    InvitationCreate,
    InvitationResponse,
)
from app.modules.invitations.service import InvitationService

router = APIRouter(tags=["invitations"])


@router.post(
    "/organizations/{org_id}/invite",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_user(
    org_id: UUID,
    data: InvitationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InvitationResponse:
    invitation = await InvitationService(db).create_invitation(
        inviter_id=current_user.id,
        organization_id=org_id,
        data=data,
    )
    return InvitationResponse.model_validate(invitation)


@router.post("/invitations/accept", response_model=InvitationResponse)
async def accept_invitation(
    data: InvitationAccept,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InvitationResponse:
    invitation = await InvitationService(db).accept_invitation(
        user_id=current_user.id,
        user_email=current_user.email,
        data=data,
    )
    return InvitationResponse.model_validate(invitation)
