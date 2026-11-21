from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.const.statement import DEFAULT_CURRENCY, IMPORTED_ACCOUNT_NAME
from app.models.account import BankAccount
from app.schemas.account import BankBalanceSnapshotUpdate


async def list_accounts(db: AsyncSession) -> List[BankAccount]:
    result = await db.execute(select(BankAccount).order_by(desc(BankAccount.is_primary)))
    return list(result.scalars().all())


async def get_account(db: AsyncSession, account_id: UUID) -> Optional[BankAccount]:
    result = await db.execute(select(BankAccount).where(BankAccount.id == account_id))
    return result.scalar_one_or_none()


async def update_balance_snapshot(
    db: AsyncSession,
    account_id: UUID,
    payload: BankBalanceSnapshotUpdate,
) -> Optional[BankAccount]:
    account = await get_account(db, account_id)
    if not account:
        return None

    account.current_balance = payload.current_balance
    account.balance_as_of = payload.balance_as_of
    await db.flush()
    await db.refresh(account)
    return account


async def get_account_by_number(db: AsyncSession, account_number: str) -> Optional[BankAccount]:
    result = await db.execute(select(BankAccount).where(BankAccount.account_number == account_number))
    return result.scalar_one_or_none()


async def create_imported_account(db: AsyncSession, account_number: str) -> BankAccount:
    account = BankAccount(
        account_number=account_number,
        account_name=IMPORTED_ACCOUNT_NAME,
        currency=DEFAULT_CURRENCY,
        is_primary=False,
    )
    db.add(account)

    await db.flush()
    return account


async def lock_account(db: AsyncSession, account: BankAccount) -> None:
    await db.refresh(account, with_for_update=True)


def add_to_balance(account: BankAccount, amount: Decimal) -> None:
    account.current_balance = (account.current_balance or Decimal("0")) + amount
