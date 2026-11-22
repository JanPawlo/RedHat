"""Seed company-specific open invoices and late-payment histories for demo profiles."""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.const.card_templates import PLANNED_EXPENSES_SETTING_KEY
from app.const.demo import DEMO_PROFILES, DEMO_PROFILE_NORTHSTAR, DEMO_PROFILE_PIZZERIA
from app.models.account import BankAccount
from app.models.company import CompanyProfile
from app.models.invoice import Invoice
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

DEMO_MARKER_INVOICE = "AS-80115"
LATE_CUSTOMER = "Frankfurter Hof Catering"
LATE_CUSTOMER_IBAN = "DE44500105175407324931"
NORTHSTAR_MARKER_INVOICE = "NL-2025-8841"
NORTHSTAR_LATE_CUSTOMER = "Baltic Parcel Network"

# (name, monthly amount, day of month, category): fictional services for the demo.
DEMO_SUBSCRIPTIONS: List[Tuple[str, str, int, str]] = [
    ("GastroCloud POS Software", "-89.00", 12, "subscription"),
    ("StreamBeats Music Licence", "-39.90", 20, "other"),
]
SUBSCRIPTION_HISTORY_MONTHS = 6
DEMO_PLANNED_EXPENSE = {"label": "new pizza oven", "amount": "8500.00", "days_from_now": 22, "movable": True}

PAID_CUSTOMER_INVOICES: List[Tuple[str, int, int, str]] = [
    ("FH-2025-09", -110, 17, "2950.00"),
    ("FH-2025-10", -80, 15, "3400.00"),
    ("FH-2025-11", -50, 19, "3150.00"),
]


def _open_invoices(account: BankAccount, as_of: date) -> List[Invoice]:
    def on(days: int) -> date:
        return as_of + timedelta(days=days)

    common = {"account_id": account.id, "currency": "EUR", "validation_status": "valid", "is_validated": True}
    return [
        Invoice(
            **common,
            invoice_number="EST-2024-NZ",
            invoice_type="incoming_expense",
            issue_date=on(-10),
            due_date=on(20),
            counterparty_name="Tax Office Frankfurt am Main",
            net_amount=Decimal("21000.00"),
            gross_amount=Decimal("21000.00"),
            description="Income tax back payment for 2024",
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
            invoice_number="FLV-2025-1288",
            invoice_type="incoming_expense",
            issue_date=on(-5),
            due_date=on(25),
            counterparty_name="Fattoria La Vino GmbH",
            net_amount=Decimal("4000.00"),
            tax_amount=Decimal("760.00"),
            gross_amount=Decimal("4760.00"),
            description="Wine stock for January",
        ),
        Invoice(
            **common,
            invoice_number="FH-2025-12",
            invoice_type="outgoing_revenue",
            issue_date=on(-16),
            due_date=on(15),
            counterparty_name=LATE_CUSTOMER,
            net_amount=Decimal("3364.49"),
            tax_amount=Decimal("235.51"),
            gross_amount=Decimal("3600.00"),
            description="December catering for hotel events",
        ),
    ]


def _paid_customer_history(account: BankAccount, as_of: date) -> List[object]:
    """Past sales invoices of the late customer and the late transfers that paid them."""
    records: List[object] = []
    for number, due_offset, days_late, amount in PAID_CUSTOMER_INVOICES:
        due = as_of + timedelta(days=due_offset)
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


def _northstar_open_invoices(account: BankAccount, as_of: date) -> List[Invoice]:
    def on(days: int) -> date:
        return as_of + timedelta(days=days)

    common = {"account_id": account.id, "currency": "EUR", "validation_status": "valid", "is_validated": True}
    return [
        Invoice(
            **common,
            invoice_number=NORTHSTAR_MARKER_INVOICE,
            invoice_type="incoming_expense",
            issue_date=on(-5),
            due_date=on(24),
            counterparty_name="Northside Vehicle Workshop",
            net_amount=Decimal("3280.00"),
            tax_amount=Decimal("623.20"),
            gross_amount=Decimal("3903.20"),
            early_discount_percent=Decimal("2.00"),
            early_discount_days=10,
            description="Scheduled service and brake repairs for delivery van",
        ),
        Invoice(
            **common,
            invoice_number="EPD-2025-1942",
            invoice_type="incoming_expense",
            issue_date=on(-3),
            due_date=on(19),
            counterparty_name="Commercial Vehicle Parts Depot",
            net_amount=Decimal("1460.00"),
            tax_amount=Decimal("277.40"),
            gross_amount=Decimal("1737.40"),
            description="Replacement tires and fleet parts",
        ),
        Invoice(
            **common,
            invoice_number="BN-2025-771",
            invoice_type="outgoing_revenue",
            issue_date=on(-18),
            due_date=on(12),
            counterparty_name=NORTHSTAR_LATE_CUSTOMER,
            net_amount=Decimal("4860.00"),
            tax_amount=Decimal("923.40"),
            gross_amount=Decimal("5783.40"),
            description="Regional parcel distribution services for December",
        ),
    ]


async def _northstar_paid_customer_history(
    session: AsyncSession, account: BankAccount, as_of: date
) -> List[Invoice]:
    query = (
        select(Transaction)
        .where(
            Transaction.account_id == account.id,
            Transaction.counterparty_name == NORTHSTAR_LATE_CUSTOMER,
            Transaction.amount_base_currency > 0,
            Transaction.booking_date <= as_of,
        )
        .order_by(Transaction.booking_date.desc())
        .limit(3)
    )
    payments = list((await session.execute(query)).scalars().all())
    records: List[Invoice] = []
    delays = (12, 16, 14)
    for index, (payment, days_late) in enumerate(zip(payments, delays, strict=False), start=1):
        due = payment.booking_date - timedelta(days=days_late)
        amount = payment.amount_base_currency
        invoice = Invoice(
            account_id=account.id,
            invoice_number=f"BN-2025-DEMO-{index}",
            invoice_type="outgoing_revenue",
            issue_date=due - timedelta(days=30),
            due_date=due,
            counterparty_name=NORTHSTAR_LATE_CUSTOMER,
            net_amount=amount,
            gross_amount=amount,
            currency="EUR",
            validation_status="valid",
            is_validated=True,
            is_paid=True,
            paid_transaction=payment,
        )
        records.append(invoice)

    return records


async def _as_of(session: AsyncSession, account: BankAccount) -> date:
    query = select(func.max(Transaction.booking_date)).where(Transaction.account_id == account.id)
    return (await session.execute(query)).scalar() or date.today()


async def ensure_demo_scenario(session: AsyncSession, account: BankAccount, profile_name: str) -> bool:
    """Add the demo invoices and the late customer's history once; returns False when they already exist."""
    marker = NORTHSTAR_MARKER_INVOICE if profile_name == DEMO_PROFILE_NORTHSTAR else DEMO_MARKER_INVOICE
    existing = await session.execute(select(Invoice.id).where(Invoice.invoice_number == marker).limit(1))
    if existing.first():
        return False

    as_of = await _as_of(session, account)
    if profile_name == DEMO_PROFILE_NORTHSTAR:
        session.add_all(_northstar_open_invoices(account, as_of))
        session.add_all(await _northstar_paid_customer_history(session, account, as_of))
    elif profile_name == DEMO_PROFILE_PIZZERIA:
        session.add_all(_open_invoices(account, as_of))
        session.add_all(_paid_customer_history(account, as_of))
    else:
        return False
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


async def ensure_demo_extras(
    session: AsyncSession,
    account: BankAccount,
    company: CompanyProfile,
    profile_name: str = DEMO_PROFILE_PIZZERIA,
) -> bool:
    """Add company-specific recurring extras and a planned purchase once."""
    marker = DEMO_SUBSCRIPTIONS[0][0]
    existing = await session.execute(select(Transaction.id).where(Transaction.counterparty_name == marker).limit(1))
    added = False
    as_of = await _as_of(session, account)

    if profile_name == DEMO_PROFILE_PIZZERIA and not existing.first():
        session.add_all(_subscription_history(account, as_of))
        added = True

    settings = dict(company.settings or {})
    planned_expense = DEMO_PROFILES.get(profile_name, {}).get("planned_expense")
    if planned_expense and PLANNED_EXPENSES_SETTING_KEY not in settings:
        planned_on = as_of + timedelta(days=planned_expense["days_from_now"])
        settings[PLANNED_EXPENSES_SETTING_KEY] = [{
            "label": planned_expense["label"],
            "amount": planned_expense["amount"],
            "date": planned_on.isoformat(),
            "movable": planned_expense["movable"],
        }]
        company.settings = settings
        added = True

    if added:
        await session.flush()
        logger.info("Demo extras added: subscriptions and a planned oven purchase")
    return added
