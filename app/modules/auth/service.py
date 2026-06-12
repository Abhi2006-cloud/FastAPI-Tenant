"""
AUTH MODULE — service.py

Business logic for registration and login.
Flow: router -> AuthService -> UserRepository + security helpers
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import UserLogin, UserRegister


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = UserRepository(db)

    async def register(self, data: UserRegister) -> User:
        """Create account; 409 if email already exists."""
        existing = await self.repo.get_by_email(data.email)
        if existing is not None:
            raise ConflictError("Email already registered")

        user = await self.repo.create(
            email=data.email,
            password_hash=hash_password(data.password),
        )
        return user

    async def login(self, data: UserLogin) -> tuple[User, str]:
        """Validate credentials and return (user, jwt_string)."""
        user = await self.repo.get_by_email(data.email)
        if user is None or not verify_password(data.password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")

        token = create_access_token(user.id)
        return user, token

    async def get_current_user(self, user_id) -> User:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError()
        return user
