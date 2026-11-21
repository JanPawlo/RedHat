from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import not_found
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_FORECAST
from app.managers import analysis_manager
from app.models.user import User

analysis_router = APIRouter(prefix="/analysis", tags=[TAG_FORECAST], responses=RESPONSE_UNAUTHORIZED)


@analysis_router.get("", summary="Analysis page data for the current quarter, computed from the database")
async def get_analysis(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
) -> Dict[str, Any]:
    """
    KPIs, weekly money in / out with larger payments, expenses by category, team from payroll transfers,
    invoices paid vs open and summary meters for the quarter that contains the last booked transaction.
    """
    result = await analysis_manager.build_analysis(db)
    if result is None:
        raise not_found("No primary bank account")
    return result
