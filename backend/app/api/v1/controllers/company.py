from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import not_found
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_COMPANY
from app.const.messages import COMPANY_PROFILE_NOT_CONFIGURED, COMPANY_PROFILE_NOT_FOUND
from app.managers import company_manager
from app.models.user import User
from app.schemas.company import CompanyProfileResponse, CompanyProfileUpdate

company_router = APIRouter(prefix="/company", tags=[TAG_COMPANY], responses=RESPONSE_UNAUTHORIZED)


@company_router.get(
    "",
    response_model=CompanyProfileResponse,
    summary="Get the company profile and agent settings",
    responses={404: {"description": "No company profile yet (run the seed)"}},
)
async def get_company_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    One company per deployment (single-tenant). `settings` holds the agent parameters,
    e.g. `min_safety_buffer` (balance the forecast should not drop below) and `forecast_days_horizon`.
    """
    profile = await company_manager.get_company_profile(db)
    if not profile:
        raise not_found(COMPANY_PROFILE_NOT_CONFIGURED)

    return profile


@company_router.put(
    "",
    response_model=CompanyProfileResponse,
    summary="Update the company profile and agent settings",
    responses={404: {"description": "No company profile to update"}},
)
async def update_company_profile(
    payload: CompanyProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """Only the fields you send are changed. A new safety buffer is used by the next forecast right away."""
    profile = await company_manager.update_company_profile(db, payload)
    if not profile:
        raise not_found(COMPANY_PROFILE_NOT_FOUND)

    return profile
