"""
AUTH MODULE — service.py

Business logic for registration, login, refresh, logout, and session management.

Flow diagram:
  router → AuthService → [UserRepository, SessionRepository, AuthAuditRepository]
                       ↓
                  security helpers (JWT, refresh tokens, UA parsing)
                       ↓
                  EmailService (fire-and-forget new-device notification)

v2.4.0 changes:
  - login() creates a UserSession and returns (user, access_token, refresh_token, session)
  - refresh() rotates the refresh token and detects replay attacks
  - logout() revokes the session identified by the refresh token
  - logout_all() revokes all sessions for a user
  - list_sessions() returns all active sessions
  - revoke_session() allows remote logout of a specific device
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID


from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.core.redis import RedisClient
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    parse_user_agent,
    verify_password,
)
from app.modules.auth.auth_audit_model import AuthEventType
from app.modules.auth.auth_audit_repository import AuthAuditRepository
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import SessionResponse
from app.modules.auth.session_model import UserSession
from app.modules.auth.session_repository import SessionRepository

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = UserRepository(db)
        self.session_repo = SessionRepository(db)
        self.audit_repo = AuthAuditRepository(db)

    async def _revoke_sid_in_redis(self, sids: UUID | str | list[UUID | str]) -> None:
        """Store session id(s) in Redis revocation blacklist for the access token TTL."""
        if not isinstance(sids, list):
            sids = [sids]
        settings = get_settings()
        ttl = settings.access_token_expire_minutes * 60
        try:
            client = await RedisClient.get_client()
            for sid in sids:
                if sid:
                    await client.setex(f"revoked_session:{sid}", ttl, "1")
        except Exception as exc:
            logger.warning("Failed to store revoked session in Redis (failing open): %s", exc)

    # ── Registration ─────────────────────────────────────────────────────────

    async def register(self, data) -> User:
        """Create account; 409 if email already exists."""
        existing = await self.repo.get_by_email(data.email)
        if existing is not None:
            raise ConflictError("Email already registered")

        user = await self.repo.create(
            email=data.email,
            password_hash=hash_password(data.password),
        )
        return user

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(
        self,
        data,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, str, UserSession]:
        """
        Validate credentials and create a new session.

        Returns (user, access_token, refresh_token, session).
        """
        settings = get_settings()

        user = await self.repo.get_by_email(data.email)
        if user is None or not verify_password(data.password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")

        # ── Enforce MAX_ACTIVE_SESSIONS: evict oldest if needed ──────────────
        active_count = await self.session_repo.count_active_by_user(user.id)
        if active_count >= settings.max_active_sessions:
            oldest = await self.session_repo.get_oldest_active(user.id)
            if oldest:
                logger.info(
                    "MAX_ACTIVE_SESSIONS reached for user=%s, evicting session=%s",
                    user.id,
                    oldest.id,
                )
                await self.session_repo.revoke(oldest)

        # ── Create session ────────────────────────────────────────────────────
        session_id = uuid.uuid4()
        raw_refresh_token = generate_refresh_token(session_id)
        token_hash = hash_refresh_token(raw_refresh_token)
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

        ua_info = parse_user_agent(user_agent)
        session = await self.session_repo.create(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=token_hash,
            expires_at=expires_at,
            device_name=ua_info.get("device_name"),
            platform=ua_info.get("platform"),
            browser=ua_info.get("browser"),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # ── Generate access token ─────────────────────────────────────────────
        access_token = create_access_token(user.id, session_id=session.id)

        # ── Audit log ─────────────────────────────────────────────────────────
        await self.audit_repo.create_event(
            user_id=user.id,
            event_type=AuthEventType.LOGIN,
            session_id=session.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"email": user.email, "device": ua_info.get("device_name")},
        )

        # ── New device email (fire-and-forget) ────────────────────────────────
        self._enqueue_new_device_email(user=user, session=session, ua_info=ua_info, ip_address=ip_address)

        return user, access_token, raw_refresh_token, session

    def _enqueue_new_device_email(
        self,
        *,
        user: User,
        session: UserSession,
        ua_info: dict,
        ip_address: str | None,
    ) -> None:
        """
        Enqueue a 'new device login' notification via a background task.

        Uses the dedicated new_device_login_email_task that creates its own
        DB session, ensuring no session-boundary issues.
        Fails silently — never raises; email is best-effort notification.
        """
        try:
            from app.jobs.email_tasks import new_device_login_email_task
            from app.services.job_service import JobService
            from app.core.config import get_settings

            settings = get_settings()
            if settings.job_sync_mode:
                return
            JobService().enqueue(

                new_device_login_email_task,
                str(user.id),
                user.email,
                {
                    "device_name": ua_info.get("device_name") or "Unknown Device",
                    "browser": ua_info.get("browser") or "Unknown Browser",
                    "platform": ua_info.get("platform") or "Unknown OS",
                    "ip_address": ip_address or "Unknown",
                    "login_time": session.created_at.strftime("%Y-%m-%d %H:%M UTC")
                    if session.created_at else "Unknown",
                    "frontend_url": settings.frontend_url,
                },
            )
        except Exception as exc:
            logger.warning("Failed to enqueue new-device login email: %s", exc)

    # ── Refresh Token ─────────────────────────────────────────────────────────

    async def refresh(
        self,
        raw_refresh_token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str, UserSession]:
        """
        Rotate a refresh token and issue a new access token.

        Returns (new_access_token, new_refresh_token, session).
        Raises UnauthorizedError on invalid/expired/revoked token.
        Detects replay attacks (token already consumed) and revokes entire session.
        """
        settings = get_settings()
        token_hash = hash_refresh_token(raw_refresh_token)

        session = None
        if "." in raw_refresh_token:
            parts = raw_refresh_token.split(".", 1)
            try:
                session_id = UUID(parts[0])
                session = await self.session_repo.get_by_id(session_id)
            except ValueError:
                pass

        if session is None:
            session = await self.session_repo.get_by_token_hash(token_hash)

        # ── Token not found ───────────────────────────────────────────────────
        if session is None:
            logger.warning(
                "Refresh token not found: ip=%s", ip_address
            )
            raise UnauthorizedError("Invalid or expired refresh token")

        # ── Replay attack detection: token hash mismatch ──────────────────────
        if session.refresh_token_hash != token_hash:
            if settings.revoke_on_refresh_replay:
                logger.error(
                    "REPLAY ATTACK detected: session=%s user=%s ip=%s",
                    session.id,
                    session.user_id,
                    ip_address,
                )
                await self.session_repo.revoke(session)
                await self._revoke_sid_in_redis(session.id)
                await self.audit_repo.create_event(
                    user_id=session.user_id,
                    event_type=AuthEventType.REPLAY_ATTACK,
                    session_id=session.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata={"token_hash_prefix": token_hash[:8]},
                )
                await self.db.commit()
            raise UnauthorizedError("Refresh token has been revoked due to replay attack")


        # ── Already revoked ───────────────────────────────────────────────────
        if session.is_revoked:
            raise UnauthorizedError("Refresh token has been revoked")

        # ── Expired ───────────────────────────────────────────────────────────
        if not session.is_active:
            raise UnauthorizedError("Refresh token has expired")

        # ── Rotate token ──────────────────────────────────────────────────────
        new_raw_token = generate_refresh_token(session.id)
        new_hash = hash_refresh_token(new_raw_token)
        new_expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

        await self.session_repo.update_token_hash(session, new_hash, new_expires_at)


        # ── Issue new access token ────────────────────────────────────────────
        new_access_token = create_access_token(session.user_id, session_id=session.id)

        # ── Audit ─────────────────────────────────────────────────────────────
        await self.audit_repo.create_event(
            user_id=session.user_id,
            event_type=AuthEventType.REFRESH,
            session_id=session.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return new_access_token, new_raw_token, session

    # ── Logout ────────────────────────────────────────────────────────────────

    async def logout(
        self,
        raw_refresh_token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Revoke the session identified by the refresh token."""
        token_hash = hash_refresh_token(raw_refresh_token)
        session = await self.session_repo.get_by_token_hash(token_hash)

        if session is None or session.is_revoked:
            # Idempotent: silently succeed if already revoked/unknown
            return

        await self.session_repo.revoke(session)
        await self._revoke_sid_in_redis(session.id)

        await self.audit_repo.create_event(
            user_id=session.user_id,
            event_type=AuthEventType.LOGOUT,
            session_id=session.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    # ── Logout All ────────────────────────────────────────────────────────────

    async def logout_all(
        self,
        user_id: UUID,
        *,
        raw_refresh_token: str | None = None,
        keep_current: bool = True,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> int:
        """
        Revoke all sessions for a user.

        If keep_current=True and raw_refresh_token is set, the current
        session is preserved.  Returns count of revoked sessions.
        """
        current_session_id: UUID | None = None
        if keep_current and raw_refresh_token:
            token_hash = hash_refresh_token(raw_refresh_token)
            current_session = await self.session_repo.get_by_token_hash(token_hash)
            if current_session and not current_session.is_revoked:
                current_session_id = current_session.id

        active_sessions = await self.session_repo.list_active_by_user(user_id)
        sids_to_revoke = [s.id for s in active_sessions if s.id != current_session_id]

        count = await self.session_repo.revoke_all_for_user(
            user_id, except_session_id=current_session_id
        )
        await self._revoke_sid_in_redis(sids_to_revoke)

        await self.audit_repo.create_event(
            user_id=user_id,
            event_type=AuthEventType.LOGOUT_ALL,
            session_id=current_session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"sessions_revoked": count, "kept_current": keep_current},
        )

        return count

    # ── Session Listing ───────────────────────────────────────────────────────

    async def list_sessions(
        self,
        user_id: UUID,
        current_session_id: UUID | None = None,
    ) -> list[SessionResponse]:
        """Return all active sessions for a user, marking the current one."""
        sessions = await self.session_repo.list_active_by_user(user_id)
        result = []
        for s in sessions:
            resp = SessionResponse(
                id=s.id,
                device_name=s.device_name,
                platform=s.platform,
                browser=s.browser,
                ip_address=s.ip_address,
                created_at=s.created_at,
                last_used_at=s.last_used_at,
                expires_at=s.expires_at,
                is_current=(s.id == current_session_id),
                is_active=s.is_active,
            )
            result.append(resp)
        return result

    # ── Remote Session Revocation ─────────────────────────────────────────────

    async def revoke_session(
        self,
        requesting_user_id: UUID,
        session_id: UUID,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Revoke a specific session by ID.

        Raises ForbiddenError if the session belongs to a different user.
        """
        session = await self.session_repo.get_by_id(session_id)
        if session is None:
            raise ForbiddenError("Session not found")
        if session.user_id != requesting_user_id:
            raise ForbiddenError("Cannot revoke a session that doesn't belong to you")
        if session.is_revoked:
            return  # idempotent

        await self.session_repo.revoke(session)
        await self._revoke_sid_in_redis(session.id)

        await self.audit_repo.create_event(
            user_id=requesting_user_id,
            event_type=AuthEventType.SESSION_REVOKED,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    # ── Change Password (G7) ──────────────────────────────────────────────────

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
        *,
        current_session_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """G7: Verify current password, enforce length rules, revoke all other sessions and tokens."""
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")

        if not verify_password(current_password, user.password_hash):
            raise BadRequestError("Current password is incorrect")

        if len(new_password) < 8:
            raise BadRequestError("New password must be at least 8 characters")

        user.password_hash = hash_password(new_password)
        await self.repo.save(user)

        # Revoke all active sessions for user in database and Redis (clean invalidation)
        active_sessions = await self.session_repo.list_active_by_user(user_id)
        sids_to_revoke = [s.id for s in active_sessions]
        if current_session_id and current_session_id not in sids_to_revoke:
            sids_to_revoke.append(current_session_id)
        await self.session_repo.revoke_all_for_user(user_id)
        await self._revoke_sid_in_redis(sids_to_revoke)

        await self.audit_repo.create_event(
            user_id=user_id,
            event_type=AuthEventType.PASSWORD_CHANGE,
            session_id=current_session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"revoked_other_sessions": len(sids_to_revoke)},
        )

    # ── get_current_user (used by dependencies.py) ───────────────────────────

    async def get_current_user(self, user_id: UUID) -> User:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError()
        return user


# ── Async helper (fire-and-forget email) ────────────────────────────────────


async def _send_new_device_email_async(
    *,
    email_service,
    user: User,
    session: UserSession,
    ua_info: dict,
    ip_address: str | None,
) -> None:
    """
    Send a 'new device login' notification email.

    Called as a background coroutine — errors are logged, never raised.
    """
    try:
        settings = get_settings()
        await email_service.queue_email(
            recipient_email=user.email,
            subject=f"New login detected on {ua_info.get('device_name') or 'a new device'}",
            template_name="new_device_login",
            context={
                "device_name": ua_info.get("device_name") or "Unknown Device",
                "browser": ua_info.get("browser") or "Unknown Browser",
                "platform": ua_info.get("platform") or "Unknown OS",
                "ip_address": ip_address or "Unknown",
                "login_time": session.created_at.strftime("%Y-%m-%d %H:%M UTC"),
                "frontend_url": settings.frontend_url,
            },
        )
    except Exception as exc:
        logger.warning("New-device email delivery failed: %s", exc)
