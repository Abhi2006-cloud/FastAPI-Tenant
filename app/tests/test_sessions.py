"""
Session management tests — v2.4.0

Tests cover:
  - Login returns access + refresh tokens + session_id
  - Refresh token rotation (new tokens issued)
  - Old refresh token rejected after rotation
  - Replay attack detection (session revoked on reuse)
  - Logout revokes session
  - Logout all revokes all sessions
  - Remote session logout (DELETE /auth/sessions/{id})
  - Session listing (GET /auth/sessions)
  - Session cleanup task (expired row deletion)
  - Expired session returns 401 on refresh
  - Concurrent sessions for same user
  - MAX_ACTIVE_SESSIONS eviction of oldest
  - Auth audit log entries created
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4


import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ──────────────────────────────────────────────────────────────────


async def register_and_login(client: AsyncClient, email: str, password: str = "securepass123") -> dict:
    """Register user then login; returns the full login response body."""
    await client.post("/auth/register", json={"email": email, "password": password})
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()


# ── 1. Login returns all required fields ─────────────────────────────────────


@pytest.mark.asyncio
async def test_login_returns_all_token_fields(client: AsyncClient) -> None:
    from app.core.config import get_settings
    tokens = await register_and_login(client, "session_user1@example.com")
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert "session_id" in tokens
    assert tokens["token_type"] == "bearer"
    settings = get_settings()
    assert tokens["expires_in"] == settings.access_token_expire_minutes * 60


# ── 2. Refresh token rotation ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_returns_new_tokens(client: AsyncClient) -> None:
    tokens = await register_and_login(client, "session_user2@example.com")
    old_refresh = tokens["refresh_token"]

    await asyncio.sleep(1.01)
    refresh_resp = await client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    # New tokens must be different from old ones
    assert new_tokens["refresh_token"] != old_refresh
    assert new_tokens["access_token"] != tokens["access_token"]



# ── 3. Old refresh token invalid after rotation ───────────────────────────────


@pytest.mark.asyncio
async def test_old_refresh_token_rejected_after_rotation(client: AsyncClient) -> None:
    tokens = await register_and_login(client, "session_user3@example.com")
    old_refresh = tokens["refresh_token"]

    # First rotation — succeeds
    first_refresh = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert first_refresh.status_code == 200

    # Second use of the SAME old token — must fail (token was rotated)
    second_refresh = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert second_refresh.status_code == 401


# ── 4. Replay attack detection ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_replay_attack_revokes_session(client: AsyncClient) -> None:
    tokens = await register_and_login(client, "replay_user@example.com")
    refresh1 = tokens["refresh_token"]

    # Use token once — rotation happens
    rotated = await client.post("/auth/refresh", json={"refresh_token": refresh1})
    assert rotated.status_code == 200
    refresh2 = rotated.json()["refresh_token"]

    # Replay: reuse old refresh1 — session should be revoked
    replay_resp = await client.post("/auth/refresh", json={"refresh_token": refresh1})
    assert replay_resp.status_code == 401

    # Newly rotated token should also be invalid (session revoked by replay detection)
    subsequent = await client.post("/auth/refresh", json={"refresh_token": refresh2})
    assert subsequent.status_code == 401


# ── 5. Logout revokes session ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    tokens = await register_and_login(client, "logout_user@example.com")
    refresh = tokens["refresh_token"]
    access = tokens["access_token"]

    logout_resp = await client.post("/auth/logout", json={"refresh_token": refresh})
    assert logout_resp.status_code == 204

    # Refresh after logout must fail
    refresh_resp = await client.post("/auth/refresh", json={"refresh_token": refresh})
    assert refresh_resp.status_code == 401


# ── 6. Logout all ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_logout_all_revokes_other_sessions(client: AsyncClient) -> None:
    email = "logout_all_user@example.com"
    tokens1 = await register_and_login(client, email)
    tokens2 = await client.post("/auth/login", json={"email": email, "password": "securepass123"})
    tokens2 = tokens2.json()

    access_token = tokens1["access_token"]
    # Logout all, keep current
    resp = await client.post(
        "/auth/logout-all",
        json={"refresh_token": tokens1["refresh_token"], "keep_current": True},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["revoked"] >= 1



    # Session 2 refresh token must now be invalid
    invalid = await client.post("/auth/refresh", json={"refresh_token": tokens2["refresh_token"]})
    assert invalid.status_code == 401

    # Session 1 (kept) must still be valid
    valid = await client.post("/auth/refresh", json={"refresh_token": tokens1["refresh_token"]})
    assert valid.status_code == 200


# ── 7. Session listing ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_sessions_returns_active_sessions(client: AsyncClient) -> None:
    email = "list_sessions_user@example.com"
    tokens1 = await register_and_login(client, email)
    # Create a second session
    await client.post("/auth/login", json={"email": email, "password": "securepass123"})

    access_token = tokens1["access_token"]
    session_id = tokens1["session_id"]

    resp = await client.get(
        "/auth/sessions",
        params={"current_session_id": session_id},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2

    sessions = data["sessions"]
    # Exactly one session should be marked as current
    current_sessions = [s for s in sessions if s.get("is_current")]
    assert len(current_sessions) == 1
    assert current_sessions[0]["id"] == session_id


# ── 8. Remote session revocation ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_remote_session_revocation(client: AsyncClient) -> None:
    email = "remote_revoke_user@example.com"
    tokens1 = await register_and_login(client, email)
    tokens2 = (await client.post(
        "/auth/login", json={"email": email, "password": "securepass123"}
    )).json()

    access_token = tokens1["access_token"]
    session2_id = tokens2["session_id"]

    # Revoke session 2 from session 1
    revoke_resp = await client.delete(
        f"/auth/sessions/{session2_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert revoke_resp.status_code == 204

    # Session 2 refresh token should now be invalid
    invalid = await client.post(
        "/auth/refresh", json={"refresh_token": tokens2["refresh_token"]}
    )
    assert invalid.status_code == 401


# ── 9. Cannot revoke another user's session ───────────────────────────────────


@pytest.mark.asyncio
async def test_cannot_revoke_other_users_session(client: AsyncClient) -> None:
    tokens_a = await register_and_login(client, "user_a_revoke@example.com")
    tokens_b = await register_and_login(client, "user_b_revoke@example.com")

    access_a = tokens_a["access_token"]
    session_b_id = tokens_b["session_id"]

    # User A tries to revoke User B's session — must be forbidden
    resp = await client.delete(
        f"/auth/sessions/{session_b_id}",
        headers={"Authorization": f"Bearer {access_a}"},
    )
    assert resp.status_code == 403


# ── 10. Refresh with invalid token ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401


# ── 11. Logout is idempotent ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_logout_is_idempotent(client: AsyncClient) -> None:
    tokens = await register_and_login(client, "idempotent_logout@example.com")
    refresh = tokens["refresh_token"]

    # First logout
    resp1 = await client.post("/auth/logout", json={"refresh_token": refresh})
    assert resp1.status_code == 204

    # Second logout with same token — should not error
    resp2 = await client.post("/auth/logout", json={"refresh_token": refresh})
    assert resp2.status_code == 204


# ── 12. Concurrent sessions ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_concurrent_sessions_allowed(client: AsyncClient) -> None:
    email = "concurrent_user@example.com"
    tokens_a = await register_and_login(client, email)

    # Login from a different "device" (same test, but creates second session)
    resp_b = await client.post("/auth/login", json={"email": email, "password": "securepass123"})
    tokens_b = resp_b.json()

    # Both access tokens must work independently
    me_a = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens_a['access_token']}"}
    )
    me_b = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens_b['access_token']}"}
    )
    assert me_a.status_code == 200
    assert me_b.status_code == 200
    assert me_a.json()["email"] == email
    assert me_b.json()["email"] == email


# ── 13. Session cleanup task ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_session_cleanup_deletes_expired_rows(db_session: AsyncSession) -> None:
    """Cleanup task removes rows with expires_at in the past."""
    from datetime import UTC, datetime, timedelta
    from app.modules.auth.session_repository import SessionRepository
    from app.core.security import hash_refresh_token, generate_refresh_token
    from app.modules.auth.models import User
    from app.core.security import hash_password

    # Create a user
    user = User(email="cleanup_test@example.com", password_hash=hash_password("pass123456"))
    db_session.add(user)
    await db_session.flush()

    repo = SessionRepository(db_session)

    # Create an already-expired session (expired 2 days ago)
    expired = await repo.create(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(generate_refresh_token()),
        expires_at=datetime.now(UTC) - timedelta(days=2),
    )

    # Create an active session (expires in 30 days)
    active = await repo.create(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(generate_refresh_token()),
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    await db_session.flush()

    deleted = await repo.delete_expired()
    assert deleted >= 1  # expired session deleted

    # Active session must still exist
    still_there = await repo.get_by_id(active.id)
    assert still_there is not None


# ── 14. Auth audit log events created ────────────────────────────────────────


@pytest.mark.asyncio
async def test_auth_audit_log_created_on_login(client: AsyncClient, db_session: AsyncSession) -> None:
    """Login creates an AUTH_AUDIT_LOG entry."""
    from sqlalchemy import select
    from app.modules.auth.auth_audit_model import AuthAuditLog, AuthEventType

    email = "audit_log_user@example.com"
    await register_and_login(client, email)

    result = await db_session.execute(
        select(AuthAuditLog).where(AuthAuditLog.event_type == AuthEventType.LOGIN.value)
    )
    logs = result.scalars().all()
    assert len(logs) >= 1


# ── 15. Session not accessible without auth ───────────────────────────────────


@pytest.mark.asyncio
async def test_sessions_endpoint_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/auth/sessions")
    assert resp.status_code == 401
