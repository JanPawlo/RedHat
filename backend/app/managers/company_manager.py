from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import CompanyProfile
from app.schemas.company import CompanyProfileUpdate


async def get_company_profile(db: AsyncSession) -> Optional[CompanyProfile]:
    result = await db.execute(select(CompanyProfile).order_by(CompanyProfile.created_at).limit(1))
    return result.scalars().first()


async def update_company_profile(db: AsyncSession, payload: CompanyProfileUpdate) -> Optional[CompanyProfile]:
    profile = await get_company_profile(db)
    if not profile:
        return None

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    await db.flush()
    await db.refresh(profile)
    return profile
