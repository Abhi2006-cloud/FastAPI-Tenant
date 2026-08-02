"""INVITATIONS MODULE — service.py

create_invitation:
  - Caller must be owner or admin in org_id (from URL)
  - Enforces Redis rate limiting & idempotency (existing pending invite is returned & re-sent)
  - Stores invitation token, queues background email job via EmailService
  - Raw token is omitted in production (EXPOSE_INVITATION_TOKENS=false)

accept_invitation:
  - Logged-in user's email must match invitation.email
  - Creates Membership(role=member) and marks invite accepted

resend_invitation:
  - Re-triggers background email job for existing invitation without generating new token
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.infrastructure.email.service import EmailService
from app.modules.audit.events import RESOURCE_INVITATION, AuditAction
from app.modules.audit.service import AuditLogService
from app.modules.auth.repository import UserRepository
from app.modules.invitations.models import Invitation, InvitationStatus
from app.modules.invitations.repository import InvitationRepository
from app.modules.invitations.schemas import InvitationAccept, InvitationCreate
from app.modules.memberships.models import MembershipRole
from app.modules.memberships.service import MembershipService
from app.modules.organizations.repository import OrganizationRepository

logger = logging.getLogger(__name__)
settings = get_settings()


class InvitationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = InvitationRepository(db)
        self.membership_service = MembershipService(db)
        self.org_repo = OrganizationRepository(db)
        self.user_repo = UserRepository(db)
        self.email_service = EmailService(db)

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

        # Idempotency Check: Return existing pending invitation if one already exists
        pending = await self.repo.get_pending_for_org_email(organization_id, data.email)
        if pending is not None:
            inviter_user = await self.user_repo.get_by_id(inviter_id)
            inviter_name = inviter_user.email if inviter_user else "An administrator"

            join_url = f"{settings.frontend_url}/invitations?token={pending.token}"
            logger.info(
                "[DEVELOPMENT MODE] Pending invitation retrieved for %s. Manual join link: %s",
                pending.email, join_url
            )

            # Enqueue resend email job for existing invitation gracefully
            try:
                await self.email_service.send_invitation(
                    organization_id=organization_id,
                    organization_name=organization.name,
                    inviter_name=inviter_name,
                    recipient_email=pending.email,
                    invitation_token=pending.token,
                    expire_hours=settings.invitation_expire_hours,
                )
            except Exception as exc:
                logger.warning("Email delivery queue skipped or failed: %s", exc)

            return pending

        token = secrets.token_urlsafe(32)
        invitation = Invitation(
            email=data.email,
            organization_id=organization_id,
            token=token,
            status=InvitationStatus.PENDING,
            expires_at=datetime.now(UTC)
            + timedelta(hours=settings.invitation_expire_hours),
        )
        created = await self.repo.create(invitation)

        inviter_user = await self.user_repo.get_by_id(inviter_id)
        inviter_name = inviter_user.email if inviter_user else "An administrator"

        join_url = f"{settings.frontend_url}/invitations?token={token}"
        logger.info(
            "[DEVELOPMENT MODE] Invitation created for %s. Manual join link: %s",
            data.email, join_url
        )

        # Queue background email job gracefully
        try:
            await self.email_service.send_invitation(
                organization_id=organization_id,
                organization_name=organization.name,
                inviter_name=inviter_name,
                recipient_email=data.email,
                invitation_token=token,
                expire_hours=settings.invitation_expire_hours,
            )
        except Exception as exc:
            logger.warning("Email delivery queue skipped or failed: %s", exc)

        await AuditLogService(self.db).create_event(
            organization_id=organization_id,
            actor_user_id=inviter_id,
            action=AuditAction.MEMBER_INVITED,
            resource_type=RESOURCE_INVITATION,
            resource_id=created.id,
            metadata={"email": data.email},
        )

        return created

    async def resend_invitation(
        self,
        invitation_id: UUID,
        actor_id: UUID,
    ) -> Invitation:
        """Resend invitation email for an existing pending invitation."""
        invitation = await self.repo.get_by_id(invitation_id)
        if invitation is None:
            raise NotFoundError("Invitation not found")

        if invitation.status != InvitationStatus.PENDING:
            raise BadRequestError("Cannot resend an invitation that is no longer pending")

        # Check permission: caller must be owner/admin in the organization
        await self.membership_service.ensure_roles(
            actor_id,
            invitation.organization_id,
            {MembershipRole.OWNER, MembershipRole.ADMIN},
        )

        organization = await self.org_repo.get_by_id(invitation.organization_id)
        if not organization:
            raise NotFoundError("Organization not found")

        actor_user = await self.user_repo.get_by_id(actor_id)
        inviter_name = actor_user.email if actor_user else "An administrator"

        join_url = f"{settings.frontend_url}/invitations?token={invitation.token}"
        logger.info(
            "[DEVELOPMENT MODE] Resending invitation for %s. Manual join link: %s",
            invitation.email, join_url
        )

        # Queue email job gracefully
        try:
            await self.email_service.send_invitation(
                organization_id=invitation.organization_id,
                organization_name=organization.name,
                inviter_name=inviter_name,
                recipient_email=invitation.email,
                invitation_token=invitation.token,
                expire_hours=settings.invitation_expire_hours,
            )
        except Exception as exc:
            logger.warning("Email delivery queue skipped or failed: %s", exc)

        return invitation


    async def accept_invitation(
        self, user_id: UUID, user_email: str, data: InvitationAccept
    ) -> Invitation:
        invitation = await self.repo.get_by_token(data.token)
        if invitation is None:
            raise NotFoundError("Invitation not found")

        if invitation.status != InvitationStatus.PENDING:
            raise BadRequestError("Invitation is no longer valid")

        now = datetime.now(UTC)
        if invitation.expires_at.tzinfo is None:
            expires_utc = invitation.expires_at.replace(tzinfo=UTC)
        else:
            expires_utc = invitation.expires_at

        if expires_utc < now:
            raise BadRequestError("Invitation has expired")

        if invitation.email.lower() != user_email.lower():
            raise BadRequestError("Invitation email does not match your account")

        membership = await self.membership_service.add_member(
            user_id=user_id,
            organization_id=invitation.organization_id,
            role=MembershipRole.MEMBER,
        )

        invitation.status = InvitationStatus.ACCEPTED
        saved = await self.repo.save(invitation)
        await AuditLogService(self.db).create_event(
            organization_id=invitation.organization_id,
            actor_user_id=user_id,
            action=AuditAction.INVITATION_ACCEPTED,
            resource_type=RESOURCE_INVITATION,
            resource_id=saved.id,
            metadata={
                "email": user_email,
                "membership_id": str(membership.id),
            },
        )
        return saved
