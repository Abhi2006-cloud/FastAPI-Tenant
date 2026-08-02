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

from app.core.config import get_settings

router = APIRouter(tags=["invitations"])


def _format_invitation_response(invitation) -> InvitationResponse:
    settings = get_settings()
    res = InvitationResponse.model_validate(invitation)
    mode = settings.effective_email_mode

    res.delivery_mode = mode
    join_url = f"{settings.frontend_url}/invitations?token={invitation.token}"
    res.invitation_url = join_url

    if mode == "production":
        res.delivery_status = "email_sent"
        res.message = "Invitation queued for delivery via email."
        if not settings.expose_invitation_tokens:
            res.token = None
            res.invitation_url = None
    elif mode == "console":
        res.delivery_status = "console_logged"
        res.token = invitation.token
        res.message = "Invitation logged to console. Use invitation URL for manual testing."
    else:  # development mode
        res.delivery_status = "manual_sharing_required"
        res.token = invitation.token
        res.message = (
            "Email delivery is running in Development Mode. Invitation generated successfully! "
            "Please copy and share the invitation link manually."
        )

    return res



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
    return _format_invitation_response(invitation)


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
    return _format_invitation_response(invitation)


@router.post("/invitations/{invitation_id}/resend", response_model=InvitationResponse)
async def resend_invitation(
    invitation_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InvitationResponse:
    """Resend invitation email for a pending invitation."""
    invitation = await InvitationService(db).resend_invitation(
        invitation_id=invitation_id,
        actor_id=current_user.id,
    )
    return _format_invitation_response(invitation)


