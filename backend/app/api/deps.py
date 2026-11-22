import re
from typing import Optional
from uuid import UUID

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import unauthorized
from app.const.app import DB_SESSION_SCOPE
from app.const.llm_limits import CLIENT_ID_HEADER, CLIENT_ID_PATTERN
from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.managers.auth_manager import get_user_by_email, get_user_by_id
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

db_session = Depends(get_db, scope=DB_SESSION_SCOPE)


def _parse_user_id(subject: Optional[str]) -> Optional[UUID]:
    if not subject:
        return None

    try:
        return UUID(subject)
    except ValueError:
        return None


async def _auth_disabled_user(db: AsyncSession) -> User:
    user = await get_user_by_email(db, settings.ADMIN_LOGIN)
    if not user or not user.is_active:
        raise unauthorized()

    return user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = db_session,
) -> User:
    if credentials is None and settings.AUTH_DISABLED:
        return await _auth_disabled_user(db)

    if credentials is None:
        raise unauthorized()

    user_id = _parse_user_id(decode_access_token(credentials.credentials))
    if user_id is None:
        raise unauthorized()

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise unauthorized()

    return user


async def llm_user_key(
    current_user: User = Depends(get_current_user),
    client_id: Optional[str] = Header(None, alias=CLIENT_ID_HEADER, include_in_schema=False),
) -> str:
    """
    Who asks, for the model load limits: the user, plus the browser's random id when it sends one, so people who
    share the demo login do not block each other. Fairness only; the global model slots do not depend on it.
    """
    if client_id and re.fullmatch(CLIENT_ID_PATTERN, client_id):
        return f"{current_user.id}:{client_id}"
    return str(current_user.id)
