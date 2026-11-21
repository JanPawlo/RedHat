import csv
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.const.messages import (
    NO_TRANSACTIONS_PARSED,
    STATEMENT_MALFORMED_CSV,
    STATEMENT_NOT_CSV,
    STATEMENT_TOO_LARGE,
    STATEMENT_UNKNOWN_ENCODING,
)
from app.const.statement import (
    STATEMENT_ENCODINGS,
    STATEMENT_FILE_EXTENSION,
    STATEMENT_MAX_BYTES,
    STATEMENT_MAX_MB,
    UNKNOWN_ACCOUNT_NUMBER,
)
from app.managers.account_manager import (
    add_to_balance,
    create_imported_account,
    get_account,
    get_account_by_number,
    lock_account,
)
from app.managers.transaction_manager import (
    TransactionKey,
    build_transaction,
    count_transaction_keys,
    transaction_key,
)
from app.models.account import BankAccount
from app.services.statement_parser import parse_bank_statement_csv


class StatementImportError(Exception):
    pass


class StatementAccountNotFoundError(Exception):
    pass


def _validate_file(filename: Optional[str], raw: bytes) -> None:
    if not (filename or "").lower().endswith(STATEMENT_FILE_EXTENSION):
        raise StatementImportError(STATEMENT_NOT_CSV)

    if len(raw) > STATEMENT_MAX_BYTES:
        raise StatementImportError(STATEMENT_TOO_LARGE.format(max_mb=STATEMENT_MAX_MB))


def _decode(raw: bytes) -> str:
    for encoding in STATEMENT_ENCODINGS:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise StatementImportError(STATEMENT_UNKNOWN_ENCODING)


def _parse(contents: str) -> List[Dict[str, Any]]:
    try:
        parsed_txs = parse_bank_statement_csv(contents)
    except csv.Error as exc:
        raise StatementImportError(STATEMENT_MALFORMED_CSV.format(error=exc))

    if not parsed_txs:
        raise StatementImportError(NO_TRANSACTIONS_PARSED)

    return parsed_txs


async def _resolve_account(db: AsyncSession, account_id: Optional[UUID], parsed_txs: List[Dict[str, Any]]) -> BankAccount:
    if account_id:
        account = await get_account(db, account_id)
        if not account:
            raise StatementAccountNotFoundError()
        return account

    account_number = parsed_txs[0]["account_number"] or UNKNOWN_ACCOUNT_NUMBER

    account = await get_account_by_number(db, account_number)
    if account:
        return account

    return await create_imported_account(db, account_number)


def _parsed_key(parsed: Dict[str, Any]) -> TransactionKey:
    return transaction_key(
        parsed["booking_date"],
        parsed["amount"],
        parsed["payment_reference"],
        parsed["counterparty_name"],
    )


async def filter_new_transactions(db: AsyncSession, account_id: UUID, parsed_txs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    booking_dates = [parsed["booking_date"] for parsed in parsed_txs]
    unmatched_existing = await count_transaction_keys(db, account_id, min(booking_dates), max(booking_dates))

    new_txs = []
    for parsed in parsed_txs:
        key = _parsed_key(parsed)
        if unmatched_existing[key] > 0:
            unmatched_existing[key] -= 1
            continue

        new_txs.append(parsed)

    return new_txs


async def import_bank_statement(
    db: AsyncSession,
    filename: Optional[str],
    raw: bytes,
    account_id: Optional[UUID],
) -> Tuple[int, int]:
    _validate_file(filename, raw)
    parsed_txs = _parse(_decode(raw))

    account = await _resolve_account(db, account_id, parsed_txs)
    await lock_account(db, account)

    new_txs = await filter_new_transactions(db, account.id, parsed_txs)

    for parsed in new_txs:
        db.add(build_transaction(account.id, parsed))
    add_to_balance(account, sum((parsed["amount_base_currency"] for parsed in new_txs), Decimal("0")))

    await db.flush()
    return len(new_txs), len(parsed_txs) - len(new_txs)
