from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import not_found
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_FORECAST
from app.managers import analysis_manager, page_manager
from app.models.user import User

analysis_router = APIRouter(prefix="/analysis", tags=[TAG_FORECAST], responses=RESPONSE_UNAUTHORIZED)

NO_ACCOUNT = "No primary bank account"
NOT_FOUND_RESPONSE = {404: {"description": "No primary bank account (run the seed or import a statement)"}}


def _found(result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if result is None:
        raise not_found(NO_ACCOUNT)
    return result


@analysis_router.get("", summary="Analysis page data for the current quarter, computed from the database", responses=NOT_FOUND_RESPONSE)
async def get_analysis(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
) -> Dict[str, Any]:
    """
    KPIs, weekly money in / out with larger payments, expenses by category, team from payroll transfers,
    invoices paid vs open and summary meters for the quarter that contains the last booked transaction.
    """
    return _found(await analysis_manager.build_analysis(db))


@analysis_router.get("/invoices", summary="Invoices page: open payables grouped by urgency", responses=NOT_FOUND_RESPONSE)
async def get_invoices_page(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
) -> Dict[str, Any]:
    """
    Unpaid supplier invoices sorted by due date and grouped (overdue, today, this week, later) relative to the
    forecast start date, with early payment discounts still available, plus supplier payments of that month.
    """
    return _found(await page_manager.build_invoices_page(db))


@analysis_router.get("/calendar", summary="Cash calendar: five weeks of forecast balance as heat levels", responses=NOT_FOUND_RESPONSE)
async def get_cash_calendar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
) -> Dict[str, Any]:
    """Level 1 = under the safety buffer, 5 = most room; includes approved decision cards and names the hardest week."""
    return _found(await page_manager.build_cash_calendar(db))


@analysis_router.get("/risk", summary="Risk page: business risk score and counterparties from own data", responses=NOT_FOUND_RESPONSE)
async def get_risk_page(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
) -> Dict[str, Any]:
    """
    Fixed rules, no AI: liquidity from the forecast, supplier dependency, customer concentration, taxes and FX
    from the last 90 days; counterparties from a year of transfers with late payments and invoice IBAN checks.
    """
    return _found(await page_manager.build_risk_page(db))


@analysis_router.get("/advisor-facts", summary="Engine facts the Advisor chat may quote", responses=NOT_FOUND_RESPONSE)
async def get_advisor_facts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
) -> Dict[str, Any]:
    """Balance, buffer, runway, lowest balance with and without approved cards, late clients and the next payments."""
    return _found(await page_manager.build_advisor_facts(db))
