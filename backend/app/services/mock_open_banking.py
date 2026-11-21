"""
Mock open-banking provider (PSD2 / Berlin Group style: accounts, balances, transactions).

Stands in for a real bank API so the "connected bank" flow can be shown without bank contracts.
Data is deterministic: the same day always gives the same transactions, so a second sync on the
same day imports nothing new and a sync on the next day imports only that day's bookings.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.const.bank import BANK_HISTORY_DAYS, BANK_SOURCE, BANK_TRANSACTION_INFO, MOCK_BANKS
from app.const.statement import DEFAULT_CHF_EUR_RATE, DEFAULT_CURRENCY

CHF = "CHF"


def list_banks() -> List[Dict[str, Any]]:
    return MOCK_BANKS


def find_bank(bank_id: str) -> Optional[Dict[str, Any]]:
    return next((bank for bank in MOCK_BANKS if bank["id"] == bank_id), None)


def account_numbers(bank: Dict[str, Any]) -> List[str]:
    return [account["iban"] for account in bank["accounts"]]


def account_transactions(bank: Dict[str, Any], account: Dict[str, Any], today: date) -> List[Dict[str, Any]]:
    """Bookings of the last `BANK_HISTORY_DAYS` days, in the shape `build_transaction` expects."""
    transactions = []

    for days_back in range(BANK_HISTORY_DAYS):
        day = today - timedelta(days=days_back)
        for template in account["transactions"]:
            if (day.toordinal() - template["offset"]) % template["every"] == 0:
                transactions.append(_booking(bank, account, template, day))

    return transactions


def account_balance(bank: Dict[str, Any], account: Dict[str, Any], today: date) -> Decimal:
    """Balance reported by the bank today: the opening balance plus every booking in the window."""
    bookings = account_transactions(bank, account, today)
    return account["opening_balance"] + sum((booking["amount"] for booking in bookings), Decimal("0"))


def _booking(bank: Dict[str, Any], account: Dict[str, Any], template: Dict[str, Any], day: date) -> Dict[str, Any]:
    amount = template["amount"]
    currency = account["currency"]

    return {
        "booking_date": day,
        "value_date": day,
        "amount": amount,
        "currency": currency,
        "amount_base_currency": _to_base_currency(amount, currency),
        "transaction_type": template["type"],
        "category": template["category"],
        "counterparty_name": template["counterparty"],
        "counterparty_account": None,
        "counterparty_bank_code": None,
        "payment_reference": f"{template['reference']} {day:%d.%m.%y}",
        "info": BANK_TRANSACTION_INFO,
        "is_recurring": template["every"] > 1,
        "metadata_payload": {"source": BANK_SOURCE, "bank_id": bank["id"], "bic": bank["bic"]},
    }


def _to_base_currency(amount: Decimal, currency: str) -> Decimal:
    if currency == DEFAULT_CURRENCY:
        return amount

    if currency == CHF:
        return (amount * Decimal(DEFAULT_CHF_EUR_RATE)).quantize(Decimal("0.01"))

    return amount
