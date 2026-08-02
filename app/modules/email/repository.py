"""EMAIL MODULE — repository.py"""

import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.email.models import EmailLog, EmailStatus


class EmailLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, log: EmailLog) -> EmailLog:
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def update(self, log: EmailLog) -> EmailLog:
        await self.db.commit()
        await self.db.refresh(log)
        return log


    async def get_by_id(self, log_id: uuid.UUID) -> Optional[EmailLog]:
        result = await self.db.execute(select(EmailLog).where(EmailLog.id == log_id))
        return result.scalar_one_or_none()

    async def list_logs(
        self,
        *,
        organization_id: Optional[uuid.UUID] = None,
        status: Optional[EmailStatus] = None,
        recipient_email: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[EmailLog], int]:
        stmt = select(EmailLog)
        count_stmt = select(func.count(EmailLog.id))

        if organization_id:
            stmt = stmt.where(EmailLog.organization_id == organization_id)
            count_stmt = count_stmt.where(EmailLog.organization_id == organization_id)

        if status:
            stmt = stmt.where(EmailLog.status == status)
            count_stmt = count_stmt.where(EmailLog.status == status)

        if recipient_email:
            stmt = stmt.where(EmailLog.recipient_email.ilike(f"%{recipient_email}%"))
            count_stmt = count_stmt.where(EmailLog.recipient_email.ilike(f"%{recipient_email}%"))

        stmt = stmt.order_by(EmailLog.created_at.desc()).offset(offset).limit(limit)

        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one() or 0

        logs_res = await self.db.execute(stmt)
        logs = list(logs_res.scalars().all())
        return logs, total

    async def get_stats(self, organization_id: Optional[uuid.UUID] = None) -> dict:
        stmt = select(EmailLog.status, func.count(EmailLog.id)).group_by(EmailLog.status)
        if organization_id:
            stmt = stmt.where(EmailLog.organization_id == organization_id)

        res = await self.db.execute(stmt)
        counts = {status.value: 0 for status in EmailStatus}
        total = 0
        for status, count in res.all():
            counts[status.value] = count
            total += count

        sent = counts.get("SENT", 0)
        success_rate = (sent / total * 100.0) if total > 0 else 100.0

        return {
            "total_emails": total,
            "status_counts": counts,
            "success_rate_percent": round(success_rate, 2),
        }
