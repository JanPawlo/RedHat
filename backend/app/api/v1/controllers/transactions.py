from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.const.pagination import DEFAULT_PAGE_LIMIT, TRANSACTIONS_MAX_LIMIT
from app.managers import transaction_manager
from app.models.user import User
from app.schemas.transaction import TransactionResponse

transactions_router = APIRouter(prefix="/transactions", tags=["Transactions"])


@transactions_router.get("", response_model=List[TransactionResponse])
async def list_transactions(
    account_id: Optional[UUID] = None,
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=TRANSACTIONS_MAX_LIMIT),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    return await transaction_manager.list_transactions(
        db, account_id, category, start_date, end_date, limit, offset
    )
