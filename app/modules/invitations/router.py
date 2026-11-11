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
from app.modules.invitations.models import InvitationStatus
from app.modules.organizations.repository import OrganizationRepository

router = APIRouter(tags=["invitations"])


def _format_invitation_response(invitation, plan: str = "free") -> InvitationResponse:
    settings = get_settings()
    res = InvitationResponse.model_validate(invitation)
    mode = settings.effective_email_mode
    join_url = f"{settings.frontend_url}/invitations?token={invitation.token}"
    res.invitation_url = join_url

    # Free plan invitations: delivery is manual, raw token and invitation_url always returned
    if plan == "free":
        res.delivery_mode = "manual"
        res.delivery_status = "manual_sharing_required"
        res.token = invitation.token
        res.message = "Free plan: please copy and share the invitation link manually."
        return res

    res.delivery_mode = mode
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
    org = await OrganizationRepository(db).get_by_id(org_id)
    plan_val = org.plan if org else "free"
    return _format_invitation_response(invitation, plan=plan_val)


@router.get("/organizations/{org_id}/invitations", response_model=list[InvitationResponse])
async def list_organization_invitations(
    org_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status: InvitationStatus | None = None,
) -> list[InvitationResponse]:
    """G3: List invitations (pending/accepted/revoked) for an organization. Owner/admin only."""
    invitations = await InvitationService(db).list_invitations(
        organization_id=org_id,
        actor_id=current_user.id,
        status=status,
    )
    org = await OrganizationRepository(db).get_by_id(org_id)
    plan_val = org.plan if org else "free"
    return [_format_invitation_response(inv, plan=plan_val) for inv in invitations]


@router.delete("/organizations/{org_id}/invitations/{invitation_id}", response_model=InvitationResponse)
async def revoke_organization_invitation(
    org_id: UUID,
    invitation_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InvitationResponse:
    """G4: Revoke a pending invitation. Owner/admin only."""
    invitation = await InvitationService(db).revoke_invitation(
        organization_id=org_id,
        invitation_id=invitation_id,
        actor_id=current_user.id,
    )
    org = await OrganizationRepository(db).get_by_id(org_id)
    plan_val = org.plan if org else "free"
    return _format_invitation_response(invitation, plan=plan_val)


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
    org = await OrganizationRepository(db).get_by_id(invitation.organization_id)
    plan_val = org.plan if org else "free"
    return _format_invitation_response(invitation, plan=plan_val)


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
    org = await OrganizationRepository(db).get_by_id(invitation.organization_id)
    plan_val = org.plan if org else "free"
    return _format_invitation_response(invitation, plan=plan_val)


