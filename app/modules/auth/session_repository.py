"""
AUTH MODULE — session_repository.py

Database access for UserSession rows. No business logic lives here.

All writes go through the service layer; this file only speaks SQL.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.session_model import UserSession


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        user_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        id: UUID | None = None,
        device_name: str | None = None,
        platform: str | None = None,
        browser: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserSession:
        """Insert a new session row and return it."""
        now_naive = datetime.now(UTC).replace(tzinfo=None)
        if expires_at and expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)

        kwargs: dict = {
            "user_id": user_id,
            "refresh_token_hash": refresh_token_hash,
            "expires_at": expires_at,
            "device_name": device_name,
            "platform": platform,
            "browser": browser,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "last_used_at": now_naive,
        }
        if id is not None:
            kwargs["id"] = id
        kwargs["created_at"] = now_naive
        session = UserSession(**kwargs)
        self.db.add(session)
        await self.db.flush()
        return session




    async def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        """Look up a session by its refresh token hash (for refresh/logout)."""
        result = await self.db.execute(
            select(UserSession).where(UserSession.refresh_token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, session_id: UUID) -> UserSession | None:
        """Look up a session by primary key (for remote revocation)."""
        result = await self.db.execute(
            select(UserSession).where(UserSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_active_by_user(self, user_id: UUID) -> list[UserSession]:
        """Return all non-revoked, non-expired sessions for a user."""
        result = await self.db.execute(
            select(UserSession)
            .where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_revoked == False,  # noqa: E712
                )
            )
            .order_by(UserSession.last_used_at.desc())
        )
        sessions = list(result.scalars().all())
        return [s for s in sessions if s.is_active]


    async def count_active_by_user(self, user_id: UUID) -> int:
        """Count active sessions for a user (for MAX_ACTIVE_SESSIONS check)."""
        return len(await self.list_active_by_user(user_id))

    async def get_oldest_active(self, user_id: UUID) -> UserSession | None:
        """Return the oldest active session (to evict when limit is reached)."""
        now_utc = datetime.now(UTC).replace(tzinfo=None)  # naive for SQLite compat
        result = await self.db.execute(
            select(UserSession)
            .where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_revoked == False,  # noqa: E712
                    UserSession.expires_at > now_utc,
                )
            )
            .order_by(UserSession.last_used_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def revoke(self, session: UserSession) -> None:
        """Mark a single session as revoked."""
        session.is_revoked = True
        session.revoked_at = datetime.now(UTC)
        await self.db.flush()

    async def revoke_all_for_user(
        self,
        user_id: UUID,
        except_session_id: UUID | None = None,
    ) -> int:
        """
        Revoke all active sessions for a user.

        If except_session_id is set, that session is kept alive.
        Returns the number of sessions revoked.
        """
        sessions = await self.list_active_by_user(user_id)
        now = datetime.now(UTC)
        count = 0
        for s in sessions:
            if except_session_id and str(s.id) == str(except_session_id):
                continue
            s.is_revoked = True
            s.revoked_at = now
            count += 1
        await self.db.flush()
        return count

    async def update_token_hash(
        self, session: UserSession, new_hash: str, new_expires_at: datetime
    ) -> None:
        """
        Replace the refresh token hash (token rotation).

        Called every time a refresh token is consumed so the old hash is
        immediately invalid.
        """
        session.refresh_token_hash = new_hash
        session.expires_at = new_expires_at
        session.last_used_at = datetime.now(UTC)
        await self.db.flush()

    async def touch(self, session: UserSession) -> None:
        """Update last_used_at for heartbeat / session tracking."""
        session.last_used_at = datetime.now(UTC)
        await self.db.flush()

    async def delete_expired(self) -> int:
        """
        Hard-delete sessions that have been expired for more than 24h.

        Called by the periodic cleanup background job.
        Returns number of rows deleted.
        """
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        result = await self.db.execute(
            select(UserSession).where(UserSession.expires_at < cutoff)
        )
        sessions = list(result.scalars().all())
        for s in sessions:
            await self.db.delete(s)
        await self.db.flush()
        return len(sessions)
