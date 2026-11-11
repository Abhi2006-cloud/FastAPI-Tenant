"""
BILLING MODULE — repository.py

Data access layer for upgrade requests.
"""

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.models import UpgradeRequest


class UpgradeRequestRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        organization_id: UUID,
        requested_by: UUID | None,
        requested_plan: str,
        message: str | None = None,
    ) -> UpgradeRequest:
        req = UpgradeRequest(
            organization_id=organization_id,
            requested_by=requested_by,
            requested_plan=requested_plan,
            message=message,
            status="pending",
        )
        self.db.add(req)
        await self.db.commit()
        await self.db.refresh(req)
        return req

    async def get_by_id(self, request_id: UUID) -> UpgradeRequest | None:
        query = select(UpgradeRequest).where(UpgradeRequest.id == request_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_all(self, status: str | None = None) -> list[UpgradeRequest]:
        query = select(UpgradeRequest).order_by(desc(UpgradeRequest.created_at))
        if status:
            query = query.where(UpgradeRequest.status == status)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_by_organization(self, organization_id: UUID) -> list[UpgradeRequest]:
        query = (
            select(UpgradeRequest)
            .where(UpgradeRequest.organization_id == organization_id)
            .order_by(desc(UpgradeRequest.created_at))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_status(self, req: UpgradeRequest, status: str) -> UpgradeRequest:
        req.status = status
        await self.db.commit()
        await self.db.refresh(req)
        return req

