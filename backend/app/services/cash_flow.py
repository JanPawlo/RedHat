"""Deterministic cash flow analysis for a single account and currency."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Iterable, Literal
from uuid import UUID

from app.models.transaction import Transaction

DateField = Literal["booking_date", "value_date"]
Period = Literal["day", "week", "month"]
ZERO = Decimal("0")
HUNDRED = Decimal("100")


@dataclass(frozen=True)
class DataIssue:
    """A validation error or non-blocking data quality warning."""

    code: str
    message: str
    transaction_id: UUID | None = None
    transaction_indexes: tuple[int, ...] = ()


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[DataIssue, ...]
    warnings: tuple[DataIssue, ...]
    valid_transactions: tuple[Transaction, ...]

    @property
    def is_valid(self) -> bool:
        return not self.errors


class CashFlowValidationError(ValueError):
    """Raised when invalid transaction data would make totals misleading."""

    def __init__(self, errors: tuple[DataIssue, ...]):
        self.errors = errors
        details = "; ".join(issue.message for issue in errors)
        super().__init__(f"Cash flow validation failed: {details}")


def _selected_date(transaction: Transaction, date_field: DateField) -> date | None:
    value = getattr(transaction, date_field, None)
    if isinstance(value, datetime):
        return None
    return value if isinstance(value, date) else None


def _check_request(
    start_date: date,
    end_date: date,
    date_field: str,
    period: str | None = None,
) -> None:
    if isinstance(start_date, datetime) or not isinstance(start_date, date):
        raise ValueError("start_date must be a date")
    if isinstance(end_date, datetime) or not isinstance(end_date, date):
        raise ValueError("end_date must be a date")
    if start_date > end_date:
        raise ValueError("start_date must not be after end_date")
    if date_field not in ("booking_date", "value_date"):
        raise ValueError("date_field must be 'booking_date' or 'value_date'")
    if period is not None and period not in ("day", "week", "month"):
        raise ValueError("period must be 'day', 'week', or 'month'")


def validate_transactions(
    transactions: Iterable[Transaction],
    account_id: UUID,
    currency: str,
    date_field: DateField = "booking_date",
    start_date: date | None = None,
    end_date: date | None = None,
) -> ValidationResult:
    """Validate one account/currency; report duplicates without dropping them.

    Missing/invalid amounts, dates, accounts, and currencies are blocking errors.
    Missing categories and duplicate candidates are warnings.
    """
    if date_field not in ("booking_date", "value_date"):
        raise ValueError("date_field must be 'booking_date' or 'value_date'")
    if not currency or currency != currency.upper() or len(currency) != 3:
        raise ValueError("currency must be a three-letter uppercase currency code")
    if (start_date is None) != (end_date is None):
        raise ValueError("start_date and end_date must either both be provided or both omitted")
    if start_date is not None and end_date is not None:
        _check_request(start_date, end_date, date_field)

    items = tuple(transactions)
    errors: list[DataIssue] = []
    warnings: list[DataIssue] = []
    valid: list[Transaction] = []
    fingerprint_indexes: dict[tuple[object, ...], list[int]] = defaultdict(list)

    for index, tx in enumerate(items):
        tx_id = getattr(tx, "id", None)
        row_errors: list[DataIssue] = []
        tx_account = getattr(tx, "account_id", None)
        tx_currency = getattr(tx, "currency", None)
        tx_date = _selected_date(tx, date_field)
        amount = getattr(tx, "amount", None)

        if tx_date is None:
            errors.append(DataIssue("missing_or_invalid_date", f"Transaction at index {index} has no valid {date_field}", tx_id))
            continue

        if start_date is not None and end_date is not None and not start_date <= tx_date <= end_date:
            continue

        if tx_account is None:
            row_errors.append(DataIssue("missing_account", f"Transaction at index {index} has no account_id", tx_id))
        elif tx_account != account_id:
            row_errors.append(DataIssue("account_mismatch", f"Transaction at index {index} belongs to another account", tx_id))

        if tx_currency is None or not str(tx_currency).strip():
            row_errors.append(DataIssue("missing_currency", f"Transaction at index {index} has no currency", tx_id))
        elif tx_currency != currency:
            row_errors.append(DataIssue("currency_mismatch", f"Transaction at index {index} uses {tx_currency}; expected {currency}", tx_id))

        if not isinstance(amount, Decimal) or not amount.is_finite():
            row_errors.append(DataIssue("missing_or_invalid_amount", f"Transaction at index {index} has no finite Decimal amount", tx_id))

        if row_errors:
            errors.extend(row_errors)
            continue

        category = getattr(tx, "category", None)
        if category is None or not str(category).strip():
            warnings.append(DataIssue("missing_category", f"Transaction at index {index} has no category", tx_id))
        elif str(category).strip().casefold() == "other":
            warnings.append(DataIssue("unclassified_category", f"Transaction at index {index} has an unknown or unclassified category ('other')", tx_id))

        valid.append(tx)
        fingerprint = (
            tx_account,
            tx_date,
            amount,
            tx_currency,
            getattr(tx, "transaction_type", None),
            getattr(tx, "category", None),
            getattr(tx, "counterparty_name", None),
            getattr(tx, "payment_reference", None),
        )
        fingerprint_indexes[fingerprint].append(index)

    for indexes in fingerprint_indexes.values():
        if len(indexes) > 1:
            warnings.append(
                DataIssue(
                    "possible_duplicate",
                    f"Possible duplicate transactions at indexes {', '.join(map(str, indexes))}; all are retained",
                    transaction_indexes=tuple(indexes),
                )
            )

    return ValidationResult(tuple(errors), tuple(warnings), tuple(valid))


def _validated_in_range(
    transactions: Iterable[Transaction],
    start_date: date,
    end_date: date,
    account_id: UUID,
    currency: str,
    date_field: DateField,
) -> tuple[tuple[Transaction, ...], ValidationResult]:
    _check_request(start_date, end_date, date_field)
    validation = validate_transactions(transactions, account_id, currency, date_field, start_date, end_date)
    if validation.errors:
        raise CashFlowValidationError(validation.errors)
    in_range = tuple(
        tx for tx in validation.valid_transactions
        if start_date <= _selected_date(tx, date_field) <= end_date  # type: ignore[operator]
    )
    return in_range, validation


def _totals(transactions: Iterable[Transaction]) -> dict[str, Decimal]:
    inflows = ZERO
    outflows = ZERO
    for tx in transactions:
        amount = tx.amount
        if amount > ZERO:
            inflows += amount
        elif amount < ZERO:
            outflows += -amount
    return {"inflows": inflows, "outflows": outflows, "net": inflows - outflows}


def calculate_cash_flow(
    transactions: Iterable[Transaction],
    start_date: date,
    end_date: date,
    account_id: UUID,
    currency: str,
    date_field: DateField = "booking_date",
) -> dict[str, Decimal]:
    """Return total inflows, positive-magnitude outflows, and signed net flow."""
    selected, _ = _validated_in_range(transactions, start_date, end_date, account_id, currency, date_field)
    return _totals(selected)


def _period_key(day: date, period: Period) -> str:
    if period == "day":
        return day.isoformat()
    if period == "week":
        iso = day.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    return f"{day.year:04d}-{day.month:02d}"


def _period_starts(start_date: date, end_date: date, period: Period) -> list[date]:
    if period == "day":
        result: list[date] = []
        current = start_date
        while current <= end_date:
            result.append(current)
            current += timedelta(days=1)
        return result
    if period == "week":
        current = start_date - timedelta(days=start_date.weekday())
        result = []
        while current <= end_date:
            result.append(current)
            current += timedelta(days=7)
        return result
    current = start_date.replace(day=1)
    result = []
    while current <= end_date:
        result.append(current)
        current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
    return result


def group_cash_flow(
    transactions: Iterable[Transaction],
    start_date: date,
    end_date: date,
    account_id: UUID,
    currency: str,
    period: Period,
    date_field: DateField = "booking_date",
    include_empty_periods: bool = True,
) -> list[dict[str, str | Decimal]]:
    """Group cash flows by day, ISO week, or calendar month."""
    _check_request(start_date, end_date, date_field, period)
    selected, _ = _validated_in_range(transactions, start_date, end_date, account_id, currency, date_field)
    grouped: dict[str, list[Transaction]] = defaultdict(list)
    for tx in selected:
        day = _selected_date(tx, date_field)
        assert day is not None
        grouped[_period_key(day, period)].append(tx)

    if include_empty_periods:
        keys = [_period_key(day, period) for day in _period_starts(start_date, end_date, period)]
    else:
        keys = sorted(grouped)

    output: list[dict[str, str | Decimal]] = []
    for key in keys:
        totals = _totals(grouped.get(key, ()))
        output.append({"period": key, **totals})
    return output


def expenses_by_category(
    transactions: Iterable[Transaction],
    start_date: date,
    end_date: date,
    account_id: UUID,
    currency: str,
    date_field: DateField = "booking_date",
) -> list[dict[str, str | Decimal]]:
    """Return negative transaction totals and Decimal percentage by category."""
    selected, _ = _validated_in_range(transactions, start_date, end_date, account_id, currency, date_field)
    totals: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for tx in selected:
        if tx.amount < ZERO:
            category = str(tx.category).strip() if tx.category and str(tx.category).strip() else "uncategorized"
            totals[category] += -tx.amount
    grand_total = sum(totals.values(), ZERO)
    return [
        {
            "category": category,
            "amount": amount,
            "percentage": (amount / grand_total * HUNDRED) if grand_total else ZERO,
        }
        for category, amount in sorted(totals.items())
    ]


def analyze_cash_flow(
    transactions: Iterable[Transaction],
    start_date: date,
    end_date: date,
    account_id: UUID,
    currency: str,
    date_field: DateField = "booking_date",
    include_empty_periods: bool = True,
) -> dict[str, object]:
    """Return a complete cash flow report and non-blocking data warnings."""
    _check_request(start_date, end_date, date_field)
    items = tuple(transactions)
    validation = validate_transactions(items, account_id, currency, date_field, start_date, end_date)
    if validation.errors:
        raise CashFlowValidationError(validation.errors)
    selected = tuple(
        tx for tx in validation.valid_transactions
        if start_date <= _selected_date(tx, date_field) <= end_date  # type: ignore[operator]
    )

    return {
        "account_id": account_id,
        "currency": currency,
        "start_date": start_date,
        "end_date": end_date,
        "date_field": date_field,
        "totals": _totals(selected),
        "daily": group_cash_flow(items, start_date, end_date, account_id, currency, "day", date_field, include_empty_periods),
        "weekly": group_cash_flow(items, start_date, end_date, account_id, currency, "week", date_field, include_empty_periods),
        "monthly": group_cash_flow(items, start_date, end_date, account_id, currency, "month", date_field, include_empty_periods),
        "expenses_by_category": expenses_by_category(items, start_date, end_date, account_id, currency, date_field),
        "warnings": validation.warnings,
    }
