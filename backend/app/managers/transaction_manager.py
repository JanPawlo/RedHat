from collections import Counter
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction


async def list_transactions(
    db: AsyncSession,
    account_id: Optional[UUID],
    category: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    limit: int,
    offset: int,
) -> List[Transaction]:
    query = select(Transaction).order_by(desc(Transaction.booking_date))

    if account_id:
        query = query.where(Transaction.account_id == account_id)
    if category:
        query = query.where(Transaction.category == category)
    if start_date:
        query = query.where(Transaction.booking_date >= start_date)
    if end_date:
        query = query.where(Transaction.booking_date <= end_date)

    result = await db.execute(query.offset(offset).limit(limit))
    return list(result.scalars().all())


TransactionKey = Tuple[date, Decimal, str, str]


def transaction_key(
    booking_date: date,
    amount: Decimal,
    payment_reference: Optional[str],
    counterparty_name: Optional[str],
) -> TransactionKey:
    return booking_date, amount, payment_reference or "", counterparty_name or ""


async def count_transaction_keys(
    db: AsyncSession,
    account_id: UUID,
    start_date: date,
    end_date: date,
) -> Counter:
    query = select(
        Transaction.booking_date,
        Transaction.amount,
        Transaction.payment_reference,
        Transaction.counterparty_name,
    ).where(
        Transaction.account_id == account_id,
        Transaction.booking_date >= start_date,
        Transaction.booking_date <= end_date,
    )

    result = await db.execute(query)
    return Counter(transaction_key(*row) for row in result.all())


def build_transaction(account_id: UUID, parsed: Dict[str, Any]) -> Transaction:
    return Transaction(
        account_id=account_id,
        booking_date=parsed["booking_date"],
        value_date=parsed["value_date"],
        amount=parsed["amount"],
        currency=parsed["currency"],
        amount_base_currency=parsed["amount_base_currency"],
        transaction_type=parsed["transaction_type"],
        category=parsed["category"],
        counterparty_name=parsed["counterparty_name"],
        counterparty_account=parsed["counterparty_account"],
        counterparty_bank_code=parsed["counterparty_bank_code"],
        payment_reference=parsed["payment_reference"],
        info=parsed["info"],
        is_recurring=parsed["is_recurring"],
        metadata_payload=parsed["metadata_payload"],
    )
