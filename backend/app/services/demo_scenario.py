"""
Demo scenario for Pizzeria Amalfi: open invoices that create a liquidity gap at the end of January, a
catering customer who pays late, two small subscriptions and a planned oven purchase (so every card template
has something to find). The decision cards are created by the agents (card_manager) from the forecast, not
written here.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.const.card_templates import PLANNED_EXPENSES_SETTING_KEY
from app.models.account import BankAccount
from app.models.company import CompanyProfile
from app.models.invoice import Invoice
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

DEMO_MARKER_INVOICE = "AS-80115"
LATE_CUSTOMER = "Frankfurter Hof Catering"
LATE_CUSTOMER_IBAN = "DE44500105175407324931"

# (name, monthly amount, day of month, category): fictional services for the demo.
DEMO_SUBSCRIPTIONS: List[Tuple[str, str, int, str]] = [
    ("GastroCloud POS Software", "-89.00", 12, "subscription"),
    ("StreamBeats Music Licence", "-39.90", 20, "other"),
]
SUBSCRIPTION_HISTORY_MONTHS = 6
DEMO_PLANNED_EXPENSE = {"label": "new pizza oven", "amount": "8500.00", "days_from_now": 22, "movable": True}

# (due date in days from the last booked day, days paid late, amount). Invoice numbers come from the dates, so the
# demo reads right whatever period the statement covers.
PAID_CUSTOMER_INVOICES: List[Tuple[int, int, str]] = [
    (-110, 17, "2950.00"),
    (-80, 15, "3400.00"),
    (-50, 19, "3150.00"),
]


def _month_number(prefix: str, day: date) -> str:
    """Invoice number from a prefix and a month, e.g. FH and 15 Dec 2025 give FH-2025-12."""
    return f"{prefix}-{day.year}-{day.month:02d}"


def _open_invoices(account: BankAccount, as_of: date) -> List[Invoice]:
    def on(days: int) -> date:
        return as_of + timedelta(days=days)

    common = {"account_id": account.id, "currency": "EUR", "validation_status": "valid", "is_validated": True}
    tax_year = as_of.year - 1
    wine_issued, wine_due = on(-5), on(25)
    catering_issued = on(-16)
    return [
        Invoice(
            **common,
            invoice_number=f"EST-{tax_year}-NZ",
            invoice_type="incoming_expense",
            issue_date=on(-10),
            due_date=on(20),
            counterparty_name="Tax Office Frankfurt am Main",
            net_amount=Decimal("21000.00"),
            gross_amount=Decimal("21000.00"),
            description=f"Income tax back payment for {tax_year}",
        ),
        Invoice(
            **common,
            invoice_number=DEMO_MARKER_INVOICE,
            invoice_type="incoming_expense",
            issue_date=on(-2),
            due_date=on(28),
            counterparty_name="Asimex Wholesale Ltd",
            counterparty_iban="DE33500105170011223344",
            net_amount=Decimal("6000.00"),
            tax_amount=Decimal("420.00"),
            gross_amount=Decimal("6420.00"),
            early_discount_percent=Decimal("2.00"),
            early_discount_days=10,
            description="Bulk order of flour, tomatoes and cheese",
        ),
        Invoice(
            **common,
            invoice_number=f"FLV-{wine_issued.year}-1288",
            invoice_type="incoming_expense",
            issue_date=wine_issued,
            due_date=wine_due,
            counterparty_name="Fattoria La Vino GmbH",
            net_amount=Decimal("4000.00"),
            tax_amount=Decimal("760.00"),
            gross_amount=Decimal("4760.00"),
            description=f"Wine stock for {wine_due:%B}",
        ),
        Invoice(
            **common,
            invoice_number=_month_number("FH", catering_issued),
            invoice_type="outgoing_revenue",
            issue_date=catering_issued,
            due_date=on(15),
            counterparty_name=LATE_CUSTOMER,
            net_amount=Decimal("3364.49"),
            tax_amount=Decimal("235.51"),
            gross_amount=Decimal("3600.00"),
            description=f"{catering_issued:%B} catering for hotel events",
        ),
    ]


def _paid_customer_history(account: BankAccount, as_of: date) -> List[object]:
    """Past sales invoices of the late customer and the late transfers that paid them."""
    records: List[object] = []
    for due_offset, days_late, amount in PAID_CUSTOMER_INVOICES:
        due = as_of + timedelta(days=due_offset)
        number = _month_number("FH", due)
        paid_on = due + timedelta(days=days_late)
        transfer = Transaction(
            account_id=account.id,
            booking_date=paid_on,
            value_date=paid_on,
            amount=Decimal(amount),
            currency="EUR",
            amount_base_currency=Decimal(amount),
            transaction_type="SEPA CREDIT TRANSFER",
            category="revenue_b2b",
            counterparty_name=LATE_CUSTOMER,
            counterparty_account=LATE_CUSTOMER_IBAN,
            payment_reference=f"Invoice {number}",
        )
        invoice = Invoice(
            account_id=account.id,
            invoice_number=number,
            invoice_type="outgoing_revenue",
            issue_date=due - timedelta(days=30),
            due_date=due,
            counterparty_name=LATE_CUSTOMER,
            net_amount=Decimal(amount),
            gross_amount=Decimal(amount),
            currency="EUR",
            validation_status="valid",
            is_validated=True,
            is_paid=True,
            paid_transaction=transfer,
        )
        records.extend([transfer, invoice])

    return records


async def _as_of(session: AsyncSession, account: BankAccount) -> date:
    query = select(func.max(Transaction.booking_date)).where(Transaction.account_id == account.id)
    return (await session.execute(query)).scalar() or date.today()


async def ensure_demo_scenario(session: AsyncSession, account: BankAccount) -> bool:
    """Add the demo invoices and the late customer's history once; returns False when they already exist."""
    existing = await session.execute(select(Invoice.id).where(Invoice.invoice_number == DEMO_MARKER_INVOICE).limit(1))
    if existing.first():
        return False

    as_of = await _as_of(session, account)
    session.add_all(_open_invoices(account, as_of))
    session.add_all(_paid_customer_history(account, as_of))
    await session.flush()

    logger.info("Demo scenario added: open invoices and the late-paying customer's history")
    return True


def _subscription_history(account: BankAccount, as_of: date) -> List[Transaction]:
    records: List[Transaction] = []
    for name, amount, day, category in DEMO_SUBSCRIPTIONS:
        for months_back in range(SUBSCRIPTION_HISTORY_MONTHS):
            month_index = as_of.month - 1 - months_back
            year, month = as_of.year + month_index // 12, month_index % 12 + 1
            booked = date(year, month, day)
            if booked > as_of:
                continue
            records.append(Transaction(
                account_id=account.id,
                booking_date=booked,
                value_date=booked,
                amount=Decimal(amount),
                currency="EUR",
                amount_base_currency=Decimal(amount),
                transaction_type="DIRECT DEBIT",
                category=category,
                counterparty_name=name,
                payment_reference=f"{name} monthly plan",
            ))
    return records


async def ensure_demo_extras(session: AsyncSession, account: BankAccount, company: CompanyProfile) -> bool:
    """Add the demo subscriptions and the planned oven once; returns False when they already exist."""
    marker = DEMO_SUBSCRIPTIONS[0][0]
    existing = await session.execute(select(Transaction.id).where(Transaction.counterparty_name == marker).limit(1))
    added = False
    as_of = await _as_of(session, account)

    if not existing.first():
        session.add_all(_subscription_history(account, as_of))
        added = True

    settings = dict(company.settings or {})
    if PLANNED_EXPENSES_SETTING_KEY not in settings:
        planned_on = as_of + timedelta(days=DEMO_PLANNED_EXPENSE["days_from_now"])
        settings[PLANNED_EXPENSES_SETTING_KEY] = [{
            "label": DEMO_PLANNED_EXPENSE["label"],
            "amount": DEMO_PLANNED_EXPENSE["amount"],
            "date": planned_on.isoformat(),
            "movable": DEMO_PLANNED_EXPENSE["movable"],
        }]
        company.settings = settings
        added = True

    if added:
        await session.flush()
        logger.info("Demo extras added: subscriptions and a planned oven purchase")
    return added
