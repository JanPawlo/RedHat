from typing import List
from uuid import UUID

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import bad_request, not_found
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_ACCOUNTS
from app.const.messages import ACCOUNT_NOT_FOUND
from app.managers import account_manager
from app.models.user import User
from app.schemas.account import BankAccountResponse, BankBalanceSnapshotUpdate

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


@accounts_router.put(
    "/{account_id}/balance",
    response_model=BankAccountResponse,
    summary="Record a bank balance snapshot and its date",
    responses={400: {"description": "Snapshot date cannot be in the future"}, 404: {"description": "Account not found"}},
)
async def update_balance_snapshot(
    account_id: UUID,
    payload: BankBalanceSnapshotUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    if payload.balance_as_of > date.today():
        raise bad_request("Balance snapshot date cannot be in the future")

    account = await account_manager.update_balance_snapshot(db, account_id, payload)
    if not account:
        raise not_found(ACCOUNT_NOT_FOUND)
    return account
