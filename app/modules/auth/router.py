"""
AUTH MODULE — router.py

HTTP layer only: validate input, call service, return response.
No SQL and no password hashing in this file.

Endpoints:
  POST /auth/register       — public
  POST /auth/login          — public, returns access + refresh tokens + session_id
  GET  /auth/me             — requires Bearer access token
  POST /auth/refresh        — rotate refresh token, issue new access token
  POST /auth/logout         — revoke current session
  POST /auth/logout-all     — revoke all sessions (optionally keep current)
  GET  /auth/sessions       — list active sessions for current user
  DELETE /auth/sessions/{id} — remotely revoke a specific session
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.request_context import RequestInfo, get_request_info
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    LogoutAllRequest,
    LogoutRequest,
    RefreshRequest,
    SessionListResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    return await AuthService(db).register(data)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
    request_info: Annotated[RequestInfo, Depends(get_request_info)],
) -> TokenResponse:
    """Login and receive access + refresh tokens. Creates a new device session."""
    from app.core.config import get_settings

    settings = get_settings()
    user, access_token, refresh_token, session = await AuthService(db).login(
        data,
        ip_address=request_info.ip_address,
        user_agent=request_info.user_agent,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        session_id=session.id,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Protected route: returns the currently authenticated user."""
    return current_user


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    request_info: Annotated[RequestInfo, Depends(get_request_info)],
) -> TokenResponse:
    """
    Rotate refresh token and issue a new access token.

    The submitted refresh token is immediately invalidated.
    Returns a fresh access token + new refresh token.
    """
    from app.core.config import get_settings

    settings = get_settings()
    new_access, new_refresh, session = await AuthService(db).refresh(
        data.refresh_token,
        ip_address=request_info.ip_address,
        user_agent=request_info.user_agent,
    )
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        session_id=session.id,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: LogoutRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    request_info: Annotated[RequestInfo, Depends(get_request_info)],
) -> None:
    """Revoke the session associated with the provided refresh token."""
    await AuthService(db).logout(
        data.refresh_token,
        ip_address=request_info.ip_address,
        user_agent=request_info.user_agent,
    )


@router.post("/logout-all", response_model=dict)
async def logout_all(
    data: LogoutAllRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    request_info: Annotated[RequestInfo, Depends(get_request_info)],
) -> dict:
    """
    Revoke all sessions for the current user.

    If keep_current=True and refresh_token is provided, the calling device
    session is preserved.
    """
    count = await AuthService(db).logout_all(
        current_user.id,
        raw_refresh_token=data.refresh_token,
        keep_current=data.keep_current,
        ip_address=request_info.ip_address,
        user_agent=request_info.user_agent,
    )
    return {"revoked": count}


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    current_session_id: UUID | None = None,
) -> SessionListResponse:
    """
    List all active sessions for the current user.

    Pass current_session_id (from your stored session_id) as a query param
    to get the is_current flag set correctly.
    """
    sessions = await AuthService(db).list_sessions(
        current_user.id,
        current_session_id=current_session_id,
    )
    return SessionListResponse(sessions=sessions, total=len(sessions))


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    request_info: Annotated[RequestInfo, Depends(get_request_info)],
) -> None:
    """Remotely logout a specific device session."""
    await AuthService(db).revoke_session(
        requesting_user_id=current_user.id,
        session_id=session_id,
        ip_address=request_info.ip_address,
        user_agent=request_info.user_agent,
    )
