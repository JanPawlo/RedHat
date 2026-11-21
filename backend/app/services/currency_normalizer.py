"""Bring bank transactions to the account's base currency before they are summed."""

from typing import Iterable, List

from sqlalchemy import inspect

from app.models.transaction import Transaction


def _column_values(transaction: Transaction) -> dict:
    return {attribute.key: getattr(transaction, attribute.key) for attribute in inspect(Transaction).column_attrs}


def to_base_currency(transaction: Transaction, base_currency: str) -> Transaction:
    """Return the transaction expressed in `base_currency`.

    Rows already in the base currency are returned unchanged. Foreign rows become a detached copy
    whose `amount` is the bank's converted `amount_base_currency`, so the database row is never modified.
    """
    if transaction.currency == base_currency or transaction.amount_base_currency is None:
        return transaction

    values = _column_values(transaction)
    values["amount"] = transaction.amount_base_currency
    values["currency"] = base_currency

    return Transaction(**values)


def normalize_to_base_currency(transactions: Iterable[Transaction], base_currency: str) -> List[Transaction]:
    """Return all transactions in `base_currency`, keeping their order."""
    return [to_base_currency(transaction, base_currency) for transaction in transactions]
