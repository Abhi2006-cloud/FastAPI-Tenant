"""
INVITATIONS MODULE — service.py

create_invitation:
  - Caller must be owner or admin in org_id (from URL)
  - Generates secure token + expiry; no email sent in V1

accept_invitation:
  - Logged-in user's email must match invitation.email
  - Creates Membership(role=member) and marks invite accepted
"""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.modules.auth.repository import UserRepository
from app.modules.invitations.models import Invitation, InvitationStatus
from app.modules.invitations.repository import InvitationRepository
from app.modules.invitations.schemas import InvitationAccept, InvitationCreate
from app.modules.memberships.models import MembershipRole
from app.modules.memberships.service import MembershipService
from app.modules.organizations.repository import OrganizationRepository

settings = get_settings()


class InvitationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = InvitationRepository(db)
        self.membership_service = MembershipService(db)
        self.org_repo = OrganizationRepository(db)
        self.user_repo = UserRepository(db)

    async def create_invitation(
        self,
        inviter_id: UUID,
        organization_id: UUID,
        data: InvitationCreate,
    ) -> Invitation:
        # Tenant + role check: only owner/admin can invite into this org
        await self.membership_service.ensure_roles(
            inviter_id,
            organization_id,
            {MembershipRole.OWNER, MembershipRole.ADMIN},
        )

        organization = await self.org_repo.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError("Organization not found")

        existing_user = await self.user_repo.get_by_email(data.email)
        if existing_user is not None:
            membership = await self.membership_service.repo.get_by_user_and_org(
                existing_user.id, organization_id
            )
            if membership is not None:
                raise ConflictError("User is already a member of this organization")

        pending = await self.repo.get_pending_for_org_email(organization_id, data.email)
        if pending is not None:
            raise ConflictError("A pending invitation already exists for this email")

        invitation = Invitation(
            email=data.email,
            organization_id=organization_id,
            token=secrets.token_urlsafe(32),
            status=InvitationStatus.PENDING,
            expires_at=datetime.now(UTC)
            + timedelta(hours=settings.invitation_expire_hours),
        )
        return await self.repo.create(invitation)

    async def accept_invitation(
        self, user_id: UUID, user_email: str, data: InvitationAccept
    ) -> Invitation:
        invitation = await self.repo.get_by_token(data.token)
        if invitation is None:
            raise NotFoundError("Invitation not found")

        if invitation.status != InvitationStatus.PENDING:
            raise BadRequestError("Invitation is no longer valid")

        # Handle timezone-aware comparison
        now = datetime.now(UTC)
        if invitation.expires_at.tzinfo is None:
            # If expires_at is naive, treat it as UTC
            expires_utc = invitation.expires_at.replace(tzinfo=UTC)
        else:
            expires_utc = invitation.expires_at
        
        if expires_utc < now:
            raise BadRequestError("Invitation has expired")

        if invitation.email.lower() != user_email.lower():
            raise BadRequestError("Invitation email does not match your account")

        # User joins the tenant as member
        await self.membership_service.add_member(
            user_id=user_id,
            organization_id=invitation.organization_id,
            role=MembershipRole.MEMBER,
        )

        invitation.status = InvitationStatus.ACCEPTED
        return await self.repo.save(invitation)
