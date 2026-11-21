import asyncio
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.const.auth import DEFAULT_ADMIN_FULL_NAME
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import TokenResponse, UserResponse


class EmailAlreadyRegisteredError(Exception):
    pass


class RegistrationDisabledError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == normalize_email(email)))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, email: str, password: str, full_name: Optional[str]) -> User:
    if not settings.registration_enabled:
        raise RegistrationDisabledError()

    if await get_user_by_email(db, email):
        raise EmailAlreadyRegisteredError()

    return await _create_user(db, email, password, full_name)


async def ensure_admin_account(db: AsyncSession, login: str, password: Optional[str]) -> Optional[User]:
    if not password:
        return None

    if await get_user_by_email(db, login):
        return None

    return await _create_user(db, login, password, DEFAULT_ADMIN_FULL_NAME)


async def _create_user(db: AsyncSession, email: str, password: str, full_name: Optional[str]) -> User:
    user = User(
        email=normalize_email(email),
        password_hash=await asyncio.to_thread(hash_password, password),
        full_name=full_name.strip() if full_name else None,
        is_active=True,
    )
    db.add(user)

    await db.flush()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if not user or not user.is_active:
        return None

    if not await asyncio.to_thread(verify_password, password, user.password_hash):
        return None

    return user


def build_token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )
