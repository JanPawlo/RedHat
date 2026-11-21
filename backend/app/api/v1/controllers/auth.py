from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import conflict, forbidden, unauthorized
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_AUTH
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

auth_router = APIRouter(prefix="/auth", tags=[TAG_AUTH])


@auth_router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account and get a token",
    responses={403: {"description": "Registration is disabled on this deployment"}, 409: {"description": "Email already registered"}},
)
async def register(payload: RegisterRequest, db: AsyncSession = db_session):
    """
    Creates a user and returns a JWT right away (no separate login needed).

    Open only in development unless `ALLOW_REGISTRATION` is set; on a shared deployment use the admin account.
    """
    try:
        user = await register_user(db, payload.email, payload.password, payload.full_name)
    except RegistrationDisabledError:
        raise forbidden(REGISTRATION_DISABLED)
    except EmailAlreadyRegisteredError:
        raise conflict(EMAIL_ALREADY_REGISTERED)

    return build_token_response(user)


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and get a token",
    responses={401: {"description": "Wrong login or password"}},
)
async def login(payload: LoginRequest, db: AsyncSession = db_session):
    """
    Returns a JWT (`access_token`). Paste it into **Authorize** to call the other endpoints.

    The field is called `email`, but the admin account logs in with its login (default `admin`).
    """
    user = await authenticate_user(db, payload.email, payload.password)
    if not user:
        raise unauthorized(INVALID_CREDENTIALS)

    return build_token_response(user)


@auth_router.get("/me", response_model=UserResponse, summary="Who am I", responses=RESPONSE_UNAUTHORIZED)
async def me(current_user: User = Depends(get_current_user)):
    """Returns the logged-in user. Handy to check that the token works."""
    return current_user
