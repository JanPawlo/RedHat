from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import conflict, forbidden, unauthorized
from app.const.messages import EMAIL_ALREADY_REGISTERED, INVALID_CREDENTIALS, REGISTRATION_DISABLED
from app.managers.auth_manager import (
    EmailAlreadyRegisteredError,
    RegistrationDisabledError,
    authenticate_user,
    build_token_response,
    register_user,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = db_session):
    try:
        user = await register_user(db, payload.email, payload.password, payload.full_name)
    except RegistrationDisabledError:
        raise forbidden(REGISTRATION_DISABLED)
    except EmailAlreadyRegisteredError:
        raise conflict(EMAIL_ALREADY_REGISTERED)

    return build_token_response(user)


@auth_router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = db_session):
    user = await authenticate_user(db, payload.email, payload.password)
    if not user:
        raise unauthorized(INVALID_CREDENTIALS)

    return build_token_response(user)


@auth_router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
