import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from app.services.supplier_share import supplier_shares
from tests.conftest import API_PREFIX
from tests.test_pages_api import demo_data  # noqa: F401

AS_OF = date(2025, 12, 31)


@dataclass
class Row:
    booking_date: date
    amount: Decimal
    category: Optional[str]
    counterparty_name: Optional[str]


def test_share_counts_only_supplier_payments_inside_the_window():
    rows = [
        Row(AS_OF, Decimal("-300"), "supplier", "Asimex"),
        Row(AS_OF - timedelta(days=10), Decimal("-100"), "supplier", "Fattoria"),
        Row(AS_OF - timedelta(days=200), Decimal("-5000"), "supplier", "Fattoria"),
        Row(AS_OF, Decimal("-9000"), "rent", "Landlord"),
        Row(AS_OF, Decimal("50"), "supplier", "Asimex"),
    ]

    shares = supplier_shares(rows, AS_OF)

    assert shares.total == Decimal("400")
    assert shares.top.name == "Asimex" and shares.top.pct == 75
    assert shares.pct_of("Fattoria") == 25
    assert shares.pct_of("Landlord") is None


def test_no_supplier_payments_gives_no_top():
    assert supplier_shares([], AS_OF).top is None


def test_analysis_and_risk_report_the_same_top_supplier(client, auth_headers, demo_data):  # noqa: F811
    analysis = client.get(f"{API_PREFIX}/analysis", headers=auth_headers).json()
    risk = client.get(f"{API_PREFIX}/analysis/risk", headers=auth_headers).json()

    insight = analysis["breakdown"]["insight"]
    factor = next(item for item in risk["factors"] if item["label"] == "Supplier dependency")["note"]

    analysis_match = re.match(r"(.+) is (\d+)% of supplier spend in the last 90 days", insight)
    risk_match = re.match(r"(.+) = (\d+)% of supplier spend in the last 90 days", factor)
    assert analysis_match and risk_match, (insight, factor)
    assert analysis_match.groups() == risk_match.groups()
