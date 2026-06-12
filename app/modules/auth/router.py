"""
AUTH MODULE — router.py

HTTP layer only: validate input, call service, return response.
No SQL and no password hashing in this file.

Endpoints:
  POST /auth/register  — public
  POST /auth/login     — public, returns JWT
  GET  /auth/me        — requires Bearer token (get_current_user)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.schemas import TokenResponse, UserLogin, UserRegister, UserResponse
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
) -> TokenResponse:
    _, token = await AuthService(db).login(data)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Example protected route: Depends resolves JWT before this function runs."""
    return current_user
