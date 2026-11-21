from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import not_found
from app.const.forecast import FORECAST_HORIZON_MAX_DAYS, FORECAST_HORIZON_MIN_DAYS
from app.const.messages import FORECAST_ACCOUNT_NOT_FOUND
from app.managers import forecast_manager
from app.models.user import User
from app.schemas.forecast import ForecastResponse, SimulationRequest, SimulationResponse

forecast_router = APIRouter(prefix="/forecast", tags=["Forecast Engine"])

HORIZON_QUERY = Query(None, ge=FORECAST_HORIZON_MIN_DAYS, le=FORECAST_HORIZON_MAX_DAYS, description="Days to forecast; company setting when omitted")
ACCOUNT_QUERY = Query(None, description="Bank account to forecast; the primary account when omitted")


@forecast_router.get("", response_model=ForecastResponse, summary="Cash forecast in three scenarios with indicators")
async def get_forecast(
    account_id: Optional[UUID] = ACCOUNT_QUERY,
    horizon_days: Optional[int] = HORIZON_QUERY,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    forecast = await forecast_manager.get_forecast(db, account_id, horizon_days)
    if not forecast:
        raise not_found(FORECAST_ACCOUNT_NOT_FOUND)

    return forecast


@forecast_router.post("/simulate", response_model=SimulationResponse, summary="'What if' simulation: forecast before and after the given cash changes")
async def simulate_forecast(
    payload: SimulationRequest,
    account_id: Optional[UUID] = ACCOUNT_QUERY,
    horizon_days: Optional[int] = HORIZON_QUERY,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    result = await forecast_manager.simulate_forecast(db, account_id, horizon_days, payload.changes)
    if not result:
        raise not_found(FORECAST_ACCOUNT_NOT_FOUND)

    return result
