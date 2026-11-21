"""
One definition of supplier dependency shared by the Analysis and Risk pages.

Share = payments to one supplier ÷ all payments to suppliers (category `supplier`, outflows only)
over the last SUPPLIER_SHARE_WINDOW_DAYS days ending on the forecast start date. Rent, utilities,
taxes and payroll are not suppliers, so they never dilute or win the ranking.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Iterable, Optional, Protocol, Tuple

from app.const.pages import SUPPLIER_CATEGORY, SUPPLIER_SHARE_WINDOW_DAYS

ZERO = Decimal("0")
OTHER_SUPPLIER = "Other"


class SpendRow(Protocol):
    booking_date: date
    amount: Decimal
    category: Optional[str]
    counterparty_name: Optional[str]


@dataclass(frozen=True)
class SupplierShare:
    name: str
    amount: Decimal
    pct: int


@dataclass(frozen=True)
class SupplierShares:
    start: date
    end: date
    total: Decimal
    suppliers: Tuple[SupplierShare, ...]

    @property
    def top(self) -> Optional[SupplierShare]:
        return self.suppliers[0] if self.suppliers else None

    def pct_of(self, name: str) -> Optional[int]:
        return next((supplier.pct for supplier in self.suppliers if supplier.name == name), None)


def window_start(as_of: date) -> date:
    return as_of - timedelta(days=SUPPLIER_SHARE_WINDOW_DAYS - 1)


def supplier_shares(rows: Iterable[SpendRow], as_of: date) -> SupplierShares:
    """Spend per supplier in the window, largest first, with whole-percent shares."""
    start = window_start(as_of)
    spend: Dict[str, Decimal] = defaultdict(lambda: ZERO)
    for row in rows:
        if row.category == SUPPLIER_CATEGORY and row.amount < 0 and start <= row.booking_date <= as_of:
            spend[row.counterparty_name or OTHER_SUPPLIER] += -row.amount

    total = sum(spend.values(), ZERO)
    ranked = sorted(spend.items(), key=lambda item: (-item[1], item[0]))
    suppliers = tuple(SupplierShare(name, amount, int(amount / total * 100)) for name, amount in ranked) if total else ()

    return SupplierShares(start=start, end=as_of, total=total, suppliers=suppliers)
