from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.models.transaction import Transaction
from app.services.currency_normalizer import normalize_to_base_currency, to_base_currency

ACCOUNT_ID = uuid4()


def transaction(amount: str, currency: str, amount_base: str) -> Transaction:
    return Transaction(
        id=uuid4(),
        account_id=ACCOUNT_ID,
        booking_date=date(2025, 12, 15),
        value_date=date(2025, 12, 15),
        amount=Decimal(amount),
        currency=currency,
        amount_base_currency=Decimal(amount_base),
        transaction_type="transfer",
        category="fx_transfer",
        counterparty_name="Supplier AG",
        metadata_payload={},
    )


def test_base_currency_row_is_returned_unchanged():
    row = transaction("-120.00", "EUR", "-120.00")

    assert to_base_currency(row, "EUR") is row


def test_foreign_row_uses_the_converted_amount():
    row = transaction("-4166.67", "CHF", "-4362.50")

    normalized = to_base_currency(row, "EUR")

    assert normalized.amount == Decimal("-4362.50")
    assert normalized.currency == "EUR"
    assert normalized.id == row.id
    assert normalized.category == "fx_transfer"
    assert normalized.counterparty_name == "Supplier AG"


def test_foreign_row_is_not_modified():
    row = transaction("-4166.67", "CHF", "-4362.50")

    to_base_currency(row, "EUR")

    assert row.amount == Decimal("-4166.67")
    assert row.currency == "CHF"


def test_normalize_keeps_order_and_converts_only_foreign_rows():
    rows = [transaction("100.00", "EUR", "100.00"), transaction("-50.00", "CHF", "-52.10"), transaction("-10.00", "EUR", "-10.00")]

    normalized = normalize_to_base_currency(rows, "EUR")

    assert [row.amount for row in normalized] == [Decimal("100.00"), Decimal("-52.10"), Decimal("-10.00")]
    assert {row.currency for row in normalized} == {"EUR"}
    assert normalized[0] is rows[0] and normalized[2] is rows[2]
