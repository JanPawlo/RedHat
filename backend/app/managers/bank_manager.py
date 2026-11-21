from datetime import date, timedelta
from typing import Any, Dict, List

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.const.bank import BANK_CONSENT_VALID_DAYS, BANK_STATUS_AVAILABLE, BANK_STATUS_CONNECTED
from app.managers.account_manager import lock_account
from app.managers.statement_manager import filter_new_transactions
from app.managers.transaction_manager import build_transaction
from app.models.account import BankAccount
from app.models.transaction import Transaction
from app.services import mock_open_banking


class BankNotFoundError(Exception):
    pass


class BankAlreadyConnectedError(Exception):
    pass


class BankNotConnectedError(Exception):
    pass


async def list_bank_connections(db: AsyncSession) -> List[Dict[str, Any]]:
    return [await _bank_status(db, bank) for bank in mock_open_banking.list_banks()]


async def connect_bank(db: AsyncSession, bank_id: str) -> Dict[str, Any]:
    """Simulated PSD2 consent: creates the bank's accounts with today's balance and imports their history."""
    bank = _require_bank(bank_id)
    if await _connected_accounts(db, bank):
        raise BankAlreadyConnectedError()

    today = date.today()
    for account in bank["accounts"]:
        created = _new_account(bank, account, today)
        db.add(created)
        await db.flush()

        _add_transactions(db, created, mock_open_banking.account_transactions(bank, account, today))

    await db.flush()
    return await _bank_status(db, bank)


async def sync_bank(db: AsyncSession, bank_id: str) -> Dict[str, Any]:
    """Pulls the bank's bookings again; only ones not stored yet are added, the balance is taken from the bank."""
    bank = _require_bank(bank_id)
    accounts = await _connected_accounts(db, bank)
    if not accounts:
        raise BankNotConnectedError()

    today = date.today()
    imported, skipped = 0, 0
    for stored in accounts:
        account = _template_for(bank, stored.account_number)
        bookings = mock_open_banking.account_transactions(bank, account, today)

        await lock_account(db, stored)
        new_bookings = await filter_new_transactions(db, stored.id, bookings) if bookings else []
        _add_transactions(db, stored, new_bookings)
        stored.current_balance = mock_open_banking.account_balance(bank, account, today)

        imported += len(new_bookings)
        skipped += len(bookings) - len(new_bookings)

    await db.flush()
    status = await _bank_status(db, bank)
    return {**status, "imported": imported, "skipped": skipped}


async def disconnect_bank(db: AsyncSession, bank_id: str) -> None:
    """Withdraws the consent: the bank's accounts and their transactions are removed."""
    bank = _require_bank(bank_id)
    if not await _connected_accounts(db, bank):
        raise BankNotConnectedError()

    await db.execute(delete(BankAccount).where(BankAccount.account_number.in_(mock_open_banking.account_numbers(bank))))
    await db.flush()


def _require_bank(bank_id: str) -> Dict[str, Any]:
    bank = mock_open_banking.find_bank(bank_id)
    if not bank:
        raise BankNotFoundError()

    return bank


def _template_for(bank: Dict[str, Any], account_number: str) -> Dict[str, Any]:
    return next(account for account in bank["accounts"] if account["iban"] == account_number)


def _new_account(bank: Dict[str, Any], account: Dict[str, Any], today: date) -> BankAccount:
    return BankAccount(
        account_number=account["iban"],
        account_name=account["name"],
        bank_name=bank["name"],
        bank_code=bank["bic"],
        currency=account["currency"],
        current_balance=mock_open_banking.account_balance(bank, account, today),
        is_primary=False,
    )


def _add_transactions(db: AsyncSession, account: BankAccount, bookings: List[Dict[str, Any]]) -> None:
    for booking in bookings:
        db.add(build_transaction(account.id, booking))


async def _connected_accounts(db: AsyncSession, bank: Dict[str, Any]) -> List[BankAccount]:
    numbers = mock_open_banking.account_numbers(bank)
    query = select(BankAccount).where(BankAccount.account_number.in_(numbers)).execution_options(populate_existing=True)
    result = await db.execute(query)
    return list(result.scalars().all())


async def _transaction_count(db: AsyncSession, account: BankAccount) -> int:
    result = await db.execute(select(func.count()).select_from(Transaction).where(Transaction.account_id == account.id))
    return result.scalar_one()


async def _bank_status(db: AsyncSession, bank: Dict[str, Any]) -> Dict[str, Any]:
    accounts = await _connected_accounts(db, bank)
    status = {
        "id": bank["id"],
        "name": bank["name"],
        "bic": bank["bic"],
        "country": bank["country"],
        "status": BANK_STATUS_CONNECTED if accounts else BANK_STATUS_AVAILABLE,
        "connected_at": None,
        "consent_valid_until": None,
        "last_synced_at": None,
        "accounts": [],
    }
    if not accounts:
        return status

    connected_at = min(account.created_at for account in accounts)
    status["connected_at"] = connected_at
    status["consent_valid_until"] = (connected_at + timedelta(days=BANK_CONSENT_VALID_DAYS)).date()
    status["last_synced_at"] = max(account.updated_at or account.created_at for account in accounts)
    status["accounts"] = [
        {
            "id": account.id,
            "account_number": account.account_number,
            "account_name": account.account_name,
            "currency": account.currency,
            "current_balance": account.current_balance,
            "transactions": await _transaction_count(db, account),
        }
        for account in accounts
    ]
    return status
