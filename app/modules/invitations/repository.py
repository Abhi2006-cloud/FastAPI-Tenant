"""INVITATIONS MODULE — repository.py (SQL only)."""

from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.invitations.models import Invitation, InvitationStatus


class InvitationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, invitation_id: UUID) -> Invitation | None:
        result = await self.db.execute(
            select(Invitation).where(Invitation.id == invitation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> Invitation | None:
        result = await self.db.execute(
            select(Invitation).where(Invitation.token == token)
        )
        return result.scalar_one_or_none()


    async def get_pending_for_org_email(
        self, organization_id: UUID, email: str
    ) -> Invitation | None:
        """Prevent duplicate pending invites for same email in same org."""
        result = await self.db.execute(
            select(Invitation).where(
                Invitation.organization_id == organization_id,
                Invitation.email == email,
                Invitation.status == InvitationStatus.PENDING,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_organization(
        self, organization_id: UUID, status: InvitationStatus | None = None
    ) -> list[Invitation]:
        query = select(Invitation).where(Invitation.organization_id == organization_id)
        if status is not None:
            query = query.where(Invitation.status == status)
        query = query.order_by(desc(Invitation.expires_at))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_pending_by_organization(self, organization_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(Invitation.id)).where(
                Invitation.organization_id == organization_id,
                Invitation.status == InvitationStatus.PENDING,
            )
        )
        return result.scalar() or 0

    async def create(self, invitation: Invitation) -> Invitation:
        self.db.add(invitation)
        await self.db.flush()
        await self.db.refresh(invitation)
        return invitation

    async def save(self, invitation: Invitation) -> Invitation:
        await self.db.flush()
        await self.db.refresh(invitation)
        return invitation
