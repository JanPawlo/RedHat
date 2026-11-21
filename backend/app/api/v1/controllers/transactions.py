from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_TRANSACTIONS
from app.const.pagination import DEFAULT_PAGE_LIMIT, TRANSACTIONS_MAX_LIMIT
from app.managers import transaction_manager
from app.models.user import User
from app.schemas.transaction import TransactionResponse

transactions_router = APIRouter(prefix="/transactions", tags=[TAG_TRANSACTIONS], responses=RESPONSE_UNAUTHORIZED)


@transactions_router.get("", response_model=List[TransactionResponse], summary="List booked transactions")
async def list_transactions(
    account_id: Optional[UUID] = Query(None, description="Only this account"),
    category: Optional[str] = Query(None, description="e.g. payroll, rent, tax, supplier, revenue_pos, utility, social_security, fx_transfer, other"),
    start_date: Optional[date] = Query(None, description="From this booking date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Until this booking date (inclusive)"),
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=TRANSACTIONS_MAX_LIMIT),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    Transaction history imported from bank statements. Amounts are signed (+ money in, - money out);
    `amount_base_currency` is converted to the base currency and is what the forecast engine uses.
    The category is assigned automatically during import.
    """
    return await transaction_manager.list_transactions(
        db, account_id, category, start_date, end_date, limit, offset
    )
