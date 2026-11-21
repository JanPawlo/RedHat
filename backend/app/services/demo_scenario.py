"""
Demo scenario for Pizzeria Amalfi: open invoices that create a liquidity gap at the end of January
and decision cards whose cash changes feed the forecast engine when approved.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.const.action import ACTION_STATUS_PENDING, EXECUTION_MODE_SIMULATED
from app.const.forecast import CASH_CHANGES_KEY, CHANGE_AMOUNT_KEY, CHANGE_DAY_OFFSET_KEY, CHANGE_LABEL_KEY
from app.models.account import BankAccount
from app.models.action import AgentAction
from app.models.invoice import Invoice
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

DEMO_MARKER_INVOICE = "AS-80115"
SWIPE_RIGHT_KEY = "swipe_right_label"
SWIPE_LEFT_KEY = "swipe_left_label"


def _change(day_offset: int, amount: str, label: str) -> Dict[str, Any]:
    return {CHANGE_DAY_OFFSET_KEY: day_offset, CHANGE_AMOUNT_KEY: amount, CHANGE_LABEL_KEY: label}


def _invoices(account: BankAccount, as_of: date) -> List[Invoice]:
    def on(days: int) -> date:
        return as_of + timedelta(days=days)

    return [
        Invoice(
            account_id=account.id,
            invoice_number="EST-2024-NZ",
            invoice_type="incoming_expense",
            issue_date=on(-10),
            due_date=on(20),
            counterparty_name="Tax Office Frankfurt am Main",
            net_amount=Decimal("21000.00"),
            tax_amount=Decimal("0.00"),
            gross_amount=Decimal("21000.00"),
            currency="EUR",
            validation_status="valid",
            is_validated=True,
            description="Income tax back payment for 2024",
        ),
        Invoice(
            account_id=account.id,
            invoice_number=DEMO_MARKER_INVOICE,
            invoice_type="incoming_expense",
            issue_date=on(-2),
            due_date=on(28),
            counterparty_name="Asimex Wholesale Ltd",
            counterparty_iban="DE33500105170011223344",
            net_amount=Decimal("6000.00"),
            tax_amount=Decimal("420.00"),
            gross_amount=Decimal("6420.00"),
            currency="EUR",
            early_discount_percent=Decimal("2.00"),
            early_discount_days=10,
            validation_status="valid",
            is_validated=True,
            description="Bulk order of flour, tomatoes and cheese",
        ),
        Invoice(
            account_id=account.id,
            invoice_number="FLV-2025-1288",
            invoice_type="incoming_expense",
            issue_date=on(-5),
            due_date=on(25),
            counterparty_name="Fattoria La Vino GmbH",
            net_amount=Decimal("4000.00"),
            tax_amount=Decimal("760.00"),
            gross_amount=Decimal("4760.00"),
            currency="EUR",
            validation_status="valid",
            is_validated=True,
            description="Wine stock for January",
        ),
    ]


def _card(
    title: str,
    agent_type: str,
    reason: str,
    explanation: str,
    amount: str,
    right: str,
    left: str,
    changes: List[Dict[str, Any]],
) -> AgentAction:
    return AgentAction(
        title=title,
        agent_type=agent_type,
        trigger_reason=reason,
        recommended_action=f"demo_{agent_type}",
        target_amount=Decimal(amount),
        currency="EUR",
        explanation=explanation,
        impact_simulation={CASH_CHANGES_KEY: changes, SWIPE_RIGHT_KEY: right, SWIPE_LEFT_KEY: left},
        status=ACTION_STATUS_PENDING,
        execution_mode=EXECUTION_MODE_SIMULATED,
    )


def _cards() -> List[AgentAction]:
    return [
        _card(
            "Pre-activate a €15,000 Commerzbank credit line before January 20?",
            "liquidity_guard",
            "The 2024 income tax back payment (€21,000, due Jan 20) and payroll plus the Asimex invoice on Jan 28 "
            "push the balance below the €5,000 safety buffer at the end of January.",
            "A revolving line drawn on Jan 19 covers the gap; interest is about €85 for the first month. "
            "Without it the forecast drops close to zero right after payday.",
            "15000.00",
            "Activate €15,000 line",
            "Not now",
            [_change(19, "15000.00", "Commerzbank credit line drawn"), _change(31, "-85.00", "Credit line interest")],
        ),
        _card(
            "Ask Fattoria La Vino to move invoice FLV-2025-1288 by 30 days?",
            "payables_optimizer",
            "The wine invoice (€4,760) is due Jan 25, in the tightest week of the month.",
            "Fattoria La Vino has been paid on time for a year; a 30-day extension is a common request. "
            "The payment moves from Jan 25 to Feb 24, after the January payroll and tax.",
            "4760.00",
            "Send the request",
            "Pay on time",
            [_change(25, "4760.00", "Fattoria La Vino invoice moved"), _change(55, "-4760.00", "Fattoria La Vino, new due date")],
        ),
        _card(
            "Pay Asimex invoice AS-80115 early and keep the 2% discount?",
            "payables_optimizer",
            "Asimex offers 2% off (€128.40) if invoice AS-80115 (€6,420) is paid within 10 days.",
            "Paying on Jan 8 instead of Jan 28 saves €128.40 and moves the payment out of payday week.",
            "6291.60",
            "Pay early, take 2%",
            "Pay on due date",
            [_change(8, "-6291.60", "Asimex AS-80115 paid early (-2%)"), _change(28, "6420.00", "Asimex AS-80115 no longer due")],
        ),
        _card(
            "Put €12,000 into a 1-month term deposit?",
            "investment_agent",
            "The balance is above €30,000 today and idle cash earns nothing.",
            "A 1-month deposit returns about €40 of interest on Feb 2. "
            "Check the forecast first: the money is locked during the tax payment and payday.",
            "12000.00",
            "Open the deposit",
            "Keep it liquid",
            [_change(2, "-12000.00", "Term deposit opened"), _change(33, "12040.00", "Term deposit returned with interest")],
        ),
        _card(
            "Buy the new pizza oven now for €9,500?",
            "capex_advisor",
            "The second oven is at the end of its life; the supplier offers delivery on Jan 5.",
            "Paying cash takes €9,500 out of the account right before the tax payment. Leasing is the alternative card.",
            "9500.00",
            "Buy for cash",
            "Wait",
            [_change(5, "-9500.00", "New pizza oven (cash)")],
        ),
        _card(
            "Lease the new pizza oven for €290 per month instead?",
            "capex_advisor",
            "Same oven as the cash offer, through Commerzbank equipment leasing.",
            "€290 per month from Jan 5; the cash stays in the account for the tax payment and payroll.",
            "290.00",
            "Lease the oven",
            "No leasing",
            [_change(5, "-290.00", "Oven leasing rate"), _change(36, "-290.00", "Oven leasing rate")],
        ),
    ]


async def _as_of(session: AsyncSession, account: BankAccount) -> date:
    query = select(func.max(Transaction.booking_date)).where(Transaction.account_id == account.id)
    return (await session.execute(query)).scalar() or date.today()


async def ensure_demo_scenario(session: AsyncSession, account: BankAccount) -> bool:
    """Add the demo invoices and cards once; returns False when they already exist."""
    existing = await session.execute(select(Invoice.id).where(Invoice.invoice_number == DEMO_MARKER_INVOICE).limit(1))
    if existing.first():
        return False

    as_of = await _as_of(session, account)
    session.add_all(_invoices(account, as_of))

    cards = _cards()
    _order_newest_first(cards)
    session.add_all(cards)
    await session.flush()

    logger.info("Demo scenario added: 3 open invoices and %d decision cards", len(cards))
    return True


def _order_newest_first(cards: List[AgentAction]) -> None:
    now = datetime.now(timezone.utc)
    for position, card in enumerate(cards):
        card.created_at = now - timedelta(milliseconds=position)
        card.updated_at = card.created_at
