from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import not_found
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_FORECAST
from app.const.forecast import FORECAST_HORIZON_MAX_DAYS, FORECAST_HORIZON_MIN_DAYS
from app.const.messages import AGENT_ACTION_NOT_FOUND, FORECAST_ACCOUNT_NOT_FOUND
from app.managers import forecast_manager
from app.managers.forecast_manager import ForecastActionNotFoundError
from app.models.user import User
from app.schemas.forecast import ForecastResponse, SimulationRequest, SimulationResponse

forecast_router = APIRouter(prefix="/forecast", tags=[TAG_FORECAST], responses=RESPONSE_UNAUTHORIZED)

HORIZON_QUERY = Query(None, ge=FORECAST_HORIZON_MIN_DAYS, le=FORECAST_HORIZON_MAX_DAYS, description="Days to forecast (7–90); company setting when omitted")
ACCOUNT_QUERY = Query(None, description="Bank account to forecast; the primary account when omitted")
NOT_FOUND_RESPONSE = {404: {"description": "No primary account (run the seed or import a statement) or unknown account_id"}}


@forecast_router.get(
    "",
    response_model=ForecastResponse,
    summary="Cash forecast in three scenarios with indicators",
    responses=NOT_FOUND_RESPONSE,
)
async def get_forecast(
    account_id: Optional[UUID] = ACCOUNT_QUERY,
    horizon_days: Optional[int] = HORIZON_QUERY,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    Forecasts the daily balance from the account history, without AI.

    **What it uses**
    - start: date of the last booked transaction (`as_of`) and the account balance,
    - recurring payments found in the history (rent, salaries, taxes…: same counterparty, similar amount, monthly or quarterly),
    - revenue as the average per weekday over the last 56 days, with monthly seasonality when there is a year of history,
    - variable costs as a share of revenue,
    - unpaid invoices on their due date (overdue ones on the first day),
    - safety buffer from the company settings.

    **What it returns**
    - `scenarios`: `pessimistic`, `base`, `optimistic` (revenue × factor); each has indicators
      (lowest balance and date, first day below buffer / zero, runway, free cash) and `days`
      with the balance and the top drivers of each day,
    - `recurring`: the recurring payments it found,
    - `revenue_model`: weekday averages, variable cost ratio, month factors,
    - `confidence`: share of revenue scenarios in which the balance stays above the buffer (source of the % on cards),
    - `after_decisions`: base scenario including the approved decision cards (dashed "after approved actions" line),
      `decisions_applied` lists those cards and their cash changes.

    `scenarios` show what happens if we do nothing; approving or undoing a card changes only `after_decisions`.
    """
    forecast = await forecast_manager.get_forecast(db, account_id, horizon_days)
    if not forecast:
        raise not_found(FORECAST_ACCOUNT_NOT_FOUND)

    return forecast


@forecast_router.post(
    "/simulate",
    response_model=SimulationResponse,
    summary="'What if': forecast before and after cash changes",
    responses=NOT_FOUND_RESPONSE,
)
async def simulate_forecast(
    payload: SimulationRequest,
    account_id: Optional[UUID] = ACCOUNT_QUERY,
    horizon_days: Optional[int] = HORIZON_QUERY,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    Adds one-off cash changes on top of the approved decision cards and returns both versions, nothing is saved.

    Each change: `on_date`, signed `amount` (+ money in, - money out), `label` (shown as a driver).
    A date before the forecast start counts on the first day; a date after the horizon is ignored.

    Examples: credit line `+25000`, new equipment `-10000`, moving an invoice = two changes
    (`+amount` on the old due date, `-amount` on the new one).

    `lowest_balance_change` = how much the lowest balance in the base scenario changes.
    """
    result = await forecast_manager.simulate_forecast(db, account_id, horizon_days, payload.changes)
    if not result:
        raise not_found(FORECAST_ACCOUNT_NOT_FOUND)

    return result


@forecast_router.get(
    "/actions/{action_id}/preview",
    response_model=SimulationResponse,
    summary="Effect of one decision card before you swipe",
    responses={404: {"description": "Card not found, no primary account or unknown account_id"}},
)
async def preview_action(
    action_id: UUID,
    account_id: Optional[UUID] = ACCOUNT_QUERY,
    horizon_days: Optional[int] = HORIZON_QUERY,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    `baseline` = forecast with the other approved cards, `simulated` = the same plus this card approved.
    The card's cash changes live in `impact_simulation.cash_changes` as
    `{"day_offset": 14, "amount": 15000, "label": "..."}` (days counted from the forecast start).
    A card without cash changes returns the same forecast twice (`lowest_balance_change` = 0).
    """
    try:
        result = await forecast_manager.preview_action(db, action_id, account_id, horizon_days)
    except ForecastActionNotFoundError:
        raise not_found(AGENT_ACTION_NOT_FOUND)

    if not result:
        raise not_found(FORECAST_ACCOUNT_NOT_FOUND)

    return result
