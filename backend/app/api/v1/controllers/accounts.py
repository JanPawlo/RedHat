from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import not_found
from app.const.messages import ACCOUNT_NOT_FOUND
from app.managers import account_manager
from app.models.user import User
from app.schemas.account import BankAccountResponse

accounts_router = APIRouter(prefix="/accounts", tags=["Accounts"])


@accounts_router.get("", response_model=List[BankAccountResponse])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    return await account_manager.list_accounts(db)


@accounts_router.get("/{account_id}", response_model=BankAccountResponse)
async def get_account(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    account = await account_manager.get_account(db, account_id)
    if not account:
        raise not_found(ACCOUNT_NOT_FOUND)

    return account
