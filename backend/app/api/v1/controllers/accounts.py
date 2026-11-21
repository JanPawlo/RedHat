from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import not_found
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_ACCOUNTS
from app.const.messages import ACCOUNT_NOT_FOUND
from app.managers import account_manager
from app.models.user import User
from app.schemas.account import BankAccountResponse

accounts_router = APIRouter(prefix="/accounts", tags=[TAG_ACCOUNTS], responses=RESPONSE_UNAUTHORIZED)


@accounts_router.get("", response_model=List[BankAccountResponse], summary="List bank accounts")
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    Primary account first. Accounts created by a CSV import are not primary:
    pass their `id` as `account_id` to the forecast to see a forecast for imported data.
    """
    return await account_manager.list_accounts(db)


@accounts_router.get(
    "/{account_id}",
    response_model=BankAccountResponse,
    summary="Get one bank account",
    responses={404: {"description": "Account not found"}},
)
async def get_account(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """Account details with `current_balance`, which the forecast uses as its opening balance."""
    account = await account_manager.get_account(db, account_id)
    if not account:
        raise not_found(ACCOUNT_NOT_FOUND)

    return account
