from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import not_found
from app.const.messages import COMPANY_PROFILE_NOT_CONFIGURED, COMPANY_PROFILE_NOT_FOUND
from app.managers import company_manager
from app.models.user import User
from app.schemas.company import CompanyProfileResponse, CompanyProfileUpdate

company_router = APIRouter(prefix="/company", tags=["Company"])


@company_router.get("", response_model=CompanyProfileResponse)
async def get_company_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    profile = await company_manager.get_company_profile(db)
    if not profile:
        raise not_found(COMPANY_PROFILE_NOT_CONFIGURED)

    return profile


@company_router.put("", response_model=CompanyProfileResponse)
async def update_company_profile(
    payload: CompanyProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    profile = await company_manager.update_company_profile(db, payload)
    if not profile:
        raise not_found(COMPANY_PROFILE_NOT_FOUND)

    return profile
