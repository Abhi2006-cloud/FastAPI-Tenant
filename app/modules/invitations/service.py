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
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.redis import RedisClient
from app.infrastructure.email.service import EmailService
from app.modules.audit.events import RESOURCE_INVITATION, AuditAction
from app.modules.audit.service import AuditLogService
from app.modules.auth.repository import UserRepository
from app.modules.billing.plans import get_plan_limits
from app.modules.invitations.models import Invitation, InvitationStatus
from app.modules.invitations.repository import InvitationRepository
from app.modules.invitations.schemas import InvitationAccept, InvitationCreate
from app.modules.memberships.models import MembershipRole
from app.modules.memberships.repository import MembershipRepository
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

        # ── Plan limits enforcement: max_members ──────────────────────────────
        plan_str = organization.plan or "free"
        limits = get_plan_limits(plan_str)
        membership_repo = MembershipRepository(self.db)
        current_members = await membership_repo.count_by_organization(organization_id)
        if current_members >= limits.max_members:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "PLAN_LIMIT_REACHED",
                    "limit": "max_members",
                    "current": current_members,
                    "max": limits.max_members,
                    "plan": plan_str,
                },
            )

        # ── Plan limits enforcement: invites_per_hour (Redis) ─────────────────
        current_hour = int(time.time() // 3600)
        rate_key = f"ratelimit:invite:{organization_id}:{current_hour}"
        try:
            client = await RedisClient.get_client()
            count = await client.incr(rate_key)
            if count == 1:
                await client.expire(rate_key, 3600)
            if count > limits.invites_per_hour:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "code": "PLAN_LIMIT_REACHED",
                        "limit": "invites_per_hour",
                        "current": count,
                        "max": limits.invites_per_hour,
                        "plan": plan_str,
                    },
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Redis invite rate limit check bypassed: %s", exc)

        # ── Idempotency Check: Return existing pending invitation if one already exists ──
        pending = await self.repo.get_pending_for_org_email(organization_id, data.email)
        if pending is not None:
            inviter_user = await self.user_repo.get_by_id(inviter_id)
            inviter_name = inviter_user.email if inviter_user else "An administrator"

            # Enqueue email only if plan is not free and production email enabled
            if plan_str != "free" and settings.is_production_email_enabled:
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

        # Queue background email job only when not on free plan and production email enabled
        if plan_str != "free" and settings.is_production_email_enabled:
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

    async def list_invitations(
        self,
        organization_id: UUID,
        actor_id: UUID,
        status: InvitationStatus | str | None = None,
    ) -> list[Invitation]:
        """G3: List invitations for an organization. Requires OWNER or ADMIN role."""
        await self.membership_service.ensure_roles(
            actor_id,
            organization_id,
            {MembershipRole.OWNER, MembershipRole.ADMIN},
        )
        if status is not None and isinstance(status, str):
            try:
                status = InvitationStatus(status)
            except ValueError:
                pass
        return await self.repo.list_by_organization(organization_id, status=status)

    async def revoke_invitation(
        self,
        organization_id: UUID,
        invitation_id: UUID,
        actor_id: UUID,
    ) -> Invitation:
        """G4: Revoke a pending invitation. Requires OWNER or ADMIN role."""
        await self.membership_service.ensure_roles(
            actor_id,
            organization_id,
            {MembershipRole.OWNER, MembershipRole.ADMIN},
        )
        invitation = await self.repo.get_by_id(invitation_id)
        if invitation is None or invitation.organization_id != organization_id:
            raise NotFoundError("Invitation not found")

        if invitation.status != InvitationStatus.PENDING:
            raise BadRequestError("Only pending invitations can be revoked")

        invitation.status = InvitationStatus.REVOKED
        saved = await self.repo.save(invitation)

        await AuditLogService(self.db).create_event(
            organization_id=organization_id,
            actor_user_id=actor_id,
            action=AuditAction.INVITATION_REVOKED,
            resource_type=RESOURCE_INVITATION,
            resource_id=saved.id,
            metadata={"email": invitation.email},
        )
        return saved

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

        if (organization.plan or "free") != "free" and settings.is_production_email_enabled:
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

        # Uniqueness guard (G11): Check if user is already a member before proceeding
        existing_membership = await self.membership_service.repo.get_by_user_and_org(
            user_id, invitation.organization_id
        )
        if existing_membership is not None:
            raise ConflictError("User is already a member of this organization")

        # Check max_members against organization plan
        org = await self.org_repo.get_by_id(invitation.organization_id)
        if org:
            limits = get_plan_limits(org.plan)
            membership_repo = MembershipRepository(self.db)
            current_members = await membership_repo.count_by_organization(invitation.organization_id)
            if current_members >= limits.max_members:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "code": "PLAN_LIMIT_REACHED",
                        "limit": "max_members",
                        "current": current_members,
                        "max": limits.max_members,
                        "plan": org.plan or "free",
                    },
                )

        invitation.status = InvitationStatus.ACCEPTED
        saved = await self.repo.save(invitation)

        membership = await self.membership_service.add_member(
            user_id=user_id,
            organization_id=invitation.organization_id,
            role=MembershipRole.MEMBER,
        )

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
