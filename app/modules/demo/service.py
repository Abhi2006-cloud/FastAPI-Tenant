"""
DEMO MODULE — service.py

Orchestrates non-hardcoded demo workspace generation through the real service layer.
"""

from datetime import UTC, datetime, timedelta
import io
import logging
import random
from uuid import UUID
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import UserLogin, UserRegister
from app.modules.auth.service import AuthService
from app.modules.billing.service import BillingService
from app.modules.demo.fixtures import (
    DEMO_DEFAULT_PASSWORD,
    DEMO_INVITES_FIXTURES,
    DEMO_MEMBERS_FIXTURES,
    DEMO_ORG_NAMES,
    DEMO_SAMPLE_FILES,
)
from app.modules.demo.schemas import DemoSessionResponse, DemoUpgradeResponse
from app.modules.files.service import FileService
from app.modules.invitations.schemas import InvitationAccept, InvitationCreate
from app.modules.invitations.service import InvitationService
from app.modules.memberships.models import MembershipRole
from app.modules.memberships.service import MembershipService
from app.modules.organizations.models import Organization
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.schemas import OrganizationCreate
from app.modules.organizations.service import OrganizationService

logger = logging.getLogger(__name__)


class DemoService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def lazy_cleanup(self) -> int:
        """
        Delete expired demo users and demo workspaces.
        Trims oldest demos if active count >= DEMO_MAX_ACTIVE.
        """
        settings = get_settings()
        now = datetime.now(UTC)
        cleaned_count = 0

        # 1. Clean up expired demo users
        query_expired = select(User).where(User.is_demo.is_(True), User.demo_expires_at <= now)
        res_expired = await self.db.execute(query_expired)
        expired_users = list(res_expired.scalars().all())

        # 2. Check total active demo users against DEMO_MAX_ACTIVE
        query_all = (
            select(User)
            .where(User.is_demo.is_(True))
            .order_by(User.created_at.asc())
        )
        res_all = await self.db.execute(query_all)
        active_demos = list(res_all.scalars().all())

        users_to_purge: list[User] = list(expired_users)
        if len(active_demos) >= settings.demo_max_active:
            excess = len(active_demos) - settings.demo_max_active + 1
            for u in active_demos[:excess]:
                if u not in users_to_purge:
                    users_to_purge.append(u)

        for demo_user in users_to_purge:
            try:
                # Find owned orgs and delete them completely
                org_query = select(Organization).where(Organization.owner_id == demo_user.id)
                res_orgs = await self.db.execute(org_query)
                owned_orgs = list(res_orgs.scalars().all())

                for org in owned_orgs:
                    await OrganizationService(self.db).delete_organization(
                        user_id=demo_user.id,
                        organization_id=org.id,
                        confirmed_name=org.name,
                    )

                # Delete demo user row
                await self.db.delete(demo_user)
                await self.db.commit()
                cleaned_count += 1
            except Exception as exc:
                logger.warning("Error during demo cleanup for user %s: %s", demo_user.id, exc)
                await self.db.rollback()

        return cleaned_count

    async def create_demo_session(
        self,
        ip_address: str | None = None,
        user_agent: str | None = None,
        members_count: int = 2,
        files_count: int = 2,
    ) -> DemoSessionResponse:
        """Create a complete demo session strictly through the public service layer."""
        settings = get_settings()
        await self.lazy_cleanup()

        suffix = uuid.uuid4().hex[:6]
        owner_email = f"demo-owner-{suffix}@demo.example.com"
        password = DEMO_DEFAULT_PASSWORD

        # 1. Register owner through AuthService
        auth_service = AuthService(self.db)
        registered_user = await auth_service.register(
            UserRegister(email=owner_email, password=password)
        )

        # Mark user as demo
        expires_at = datetime.now(UTC) + timedelta(hours=settings.demo_ttl_hours)
        registered_user.is_demo = True
        registered_user.demo_expires_at = expires_at
        await UserRepository(self.db).save(registered_user)
        await self.db.commit()

        # 2. Login owner through AuthService
        owner_user, access_token, refresh_token, session = await auth_service.login(
            UserLogin(email=owner_email, password=password),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # 3. Create demo organization through OrganizationService
        org_name = f"{random.choice(DEMO_ORG_NAMES)} {suffix.upper()}"
        org_service = OrganizationService(self.db)
        org = await org_service.create_organization(
            owner_id=owner_user.id,
            data=OrganizationCreate(name=org_name),
        )

        # 4. Create and accept invited members through InvitationService
        invitation_service = InvitationService(self.db)
        membership_service = MembershipService(self.db)

        for member_fixture in DEMO_MEMBERS_FIXTURES[:members_count]:
            m_email = f"{member_fixture['name_prefix']}-{suffix}@demo.example.com"
            m_user = await auth_service.register(
                UserRegister(email=m_email, password=password)
            )
            m_user.is_demo = True
            m_user.demo_expires_at = expires_at
            await UserRepository(self.db).save(m_user)
            await self.db.commit()

            # Create invite as owner
            invite = await invitation_service.create_invitation(
                inviter_id=owner_user.id,
                organization_id=org.id,
                data=InvitationCreate(email=m_email),
            )

            # Accept invite as member
            await invitation_service.accept_invitation(
                user_id=m_user.id,
                user_email=m_email,
                data=InvitationAccept(token=invite.token),
            )

            # Upgrade role if fixture specifies admin
            if member_fixture["role"] == "admin":
                membership = await membership_service.repo.get_by_user_and_org(m_user.id, org.id)
                if membership:
                    await membership_service.change_role(
                        requester_user_id=owner_user.id,
                        organization_id=org.id,
                        membership_id=membership.id,
                        new_role=MembershipRole.ADMIN,
                    )

        # 5. Create pending invitations
        for inv_email in DEMO_INVITES_FIXTURES[:1]:
            full_inv = f"{suffix}.{inv_email}"
            await invitation_service.create_invitation(
                inviter_id=owner_user.id,
                organization_id=org.id,
                data=InvitationCreate(email=full_inv),
            )

        # 6. Upload sample files through FileService
        file_service = FileService(self.db)
        for sample_file in DEMO_SAMPLE_FILES[:files_count]:
            file_stream = io.BytesIO(sample_file["content"])
            upload = UploadFile(
                file=file_stream,
                filename=sample_file["filename"],
                headers={"content-type": "text/plain"},
            )
            await file_service.upload_file(
                user_id=owner_user.id,
                organization_id=org.id,
                upload=upload,
            )

        return DemoSessionResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            session_id=session.id,
            expires_in=settings.access_token_expire_minutes * 60,
            organization_id=org.id,
        )

    async def upgrade_demo_organization(
        self,
        current_user: User,
        organization_id: UUID,
    ) -> DemoUpgradeResponse:
        """Instant upgrade from free to pro plan for demo workspaces."""
        if not current_user.is_demo:
            raise HTTPException(
                status_code=403,
                detail="Only demo workspaces can use instant demo upgrade",
            )

        org_repo = OrganizationRepository(self.db)
        org = await org_repo.get_by_id(organization_id)
        if not org:
            raise NotFoundError("Organization not found")

        if org.owner_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only the demo workspace owner can perform demo upgrade",
            )

        await BillingService(self.db).update_organization_plan(
            organization_id=organization_id,
            new_plan="pro",
            actor_user_id=current_user.id,
        )

        return DemoUpgradeResponse(
            organization_id=organization_id,
            plan="pro",
            message="Workspace successfully upgraded to Pro plan for demo testing.",
        )

