from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.const.company import DEFAULT_MIN_SAFETY_BUFFER, MIN_SAFETY_BUFFER_KEY
from app.const.forecast import (
    FORECAST_HORIZON_DEFAULT_DAYS,
    FORECAST_HORIZON_MAX_DAYS,
    FORECAST_HORIZON_MIN_DAYS,
    FORECAST_HORIZON_SETTING_KEY,
    FORECAST_INVOICE_TYPES,
    INVOICE_TYPE_REVENUE,
)
from app.managers.account_manager import get_account
from app.models.account import BankAccount
from app.models.company import CompanyProfile
from app.models.invoice import Invoice
from app.models.transaction import Transaction
from app.schemas.forecast import (
    CashChangeRequest,
    ForecastResponse,
    SimulationResponse,
)
from app.services.forecast_engine import (
    CashChange,
    CashRecord,
    Forecast,
    ForecastInputs,
    OpenInvoice,
    build_forecast,
    simulate,
)


async def get_forecast(db: AsyncSession, account_id: Optional[UUID], horizon_days: Optional[int]) -> Optional[ForecastResponse]:
    account = await _resolve_account(db, account_id)
    if not account:
        return None

    inputs, skipped = await _load_inputs(db, account, horizon_days)
    forecast = build_forecast(inputs)

    return _to_response(forecast, account, skipped)


async def simulate_forecast(
    db: AsyncSession,
    account_id: Optional[UUID],
    horizon_days: Optional[int],
    changes: Sequence[CashChangeRequest],
) -> Optional[SimulationResponse]:
    account = await _resolve_account(db, account_id)
    if not account:
        return None

    inputs, skipped = await _load_inputs(db, account, horizon_days)
    result = simulate(inputs, [CashChange(change.on_date, change.amount, change.label) for change in changes])

    return SimulationResponse(
        baseline=_to_response(result.baseline, account, skipped),
        simulated=_to_response(result.simulated, account, skipped),
        lowest_balance_change=result.lowest_balance_change,
    )


async def _resolve_account(db: AsyncSession, account_id: Optional[UUID]) -> Optional[BankAccount]:
    if account_id:
        return await get_account(db, account_id)

    query = select(BankAccount).where(BankAccount.is_primary.is_(True)).order_by(BankAccount.created_at).limit(1)
    return (await db.execute(query)).scalars().first()


async def _load_inputs(db: AsyncSession, account: BankAccount, horizon_days: Optional[int]) -> Tuple[ForecastInputs, List[str]]:
    company = await _company(db)
    history = await _history(db, account.id)
    invoices, skipped = await _open_invoices(db, account)

    inputs = ForecastInputs(
        as_of=await _as_of(db, account.id),
        opening_balance=account.current_balance,
        safety_buffer=_safety_buffer(company),
        horizon_days=horizon_days or _default_horizon(company),
        history=history,
        invoices=invoices,
    )
    return inputs, skipped


async def _company(db: AsyncSession) -> Optional[CompanyProfile]:
    query = select(CompanyProfile).order_by(CompanyProfile.created_at).limit(1)
    return (await db.execute(query)).scalars().first()


def _safety_buffer(company: Optional[CompanyProfile]) -> Decimal:
    if company and MIN_SAFETY_BUFFER_KEY in company.settings:
        return Decimal(str(company.settings[MIN_SAFETY_BUFFER_KEY]))

    return Decimal(str(DEFAULT_MIN_SAFETY_BUFFER))


def _default_horizon(company: Optional[CompanyProfile]) -> int:
    configured = company.settings.get(FORECAST_HORIZON_SETTING_KEY) if company else None
    if not isinstance(configured, int):
        return FORECAST_HORIZON_DEFAULT_DAYS

    return min(max(configured, FORECAST_HORIZON_MIN_DAYS), FORECAST_HORIZON_MAX_DAYS)


async def _as_of(db: AsyncSession, account_id: UUID) -> date:
    query = select(func.max(Transaction.booking_date)).where(Transaction.account_id == account_id)
    last_booking = (await db.execute(query)).scalar()
    return last_booking or date.today()


async def _history(db: AsyncSession, account_id: UUID) -> Tuple[CashRecord, ...]:
    query = select(
        Transaction.booking_date,
        Transaction.amount_base_currency,
        Transaction.counterparty_name,
        Transaction.category,
    ).where(Transaction.account_id == account_id)

    rows = (await db.execute(query)).all()
    return tuple(
        CashRecord(booking_date=row[0], amount=row[1], counterparty=row[2] or "", category=row[3] or "")
        for row in rows
    )


async def _open_invoices(db: AsyncSession, account: BankAccount) -> Tuple[Tuple[OpenInvoice, ...], List[str]]:
    query = select(Invoice).where(
        Invoice.is_paid.is_(False),
        Invoice.invoice_type.in_(FORECAST_INVOICE_TYPES),
        or_(Invoice.account_id == account.id, Invoice.account_id.is_(None)),
    ).order_by(Invoice.due_date)

    invoices: List[OpenInvoice] = []
    skipped: List[str] = []
    for invoice in (await db.execute(query)).scalars().all():
        if invoice.currency != account.currency:
            skipped.append(invoice.invoice_number)
            continue

        invoices.append(_to_open_invoice(invoice))

    return tuple(invoices), skipped


def _to_open_invoice(invoice: Invoice) -> OpenInvoice:
    sign = Decimal("1") if invoice.invoice_type == INVOICE_TYPE_REVENUE else Decimal("-1")
    return OpenInvoice(
        invoice_number=invoice.invoice_number,
        counterparty=invoice.counterparty_name,
        due_date=invoice.due_date,
        amount=invoice.gross_amount * sign,
    )


def _to_response(forecast: Forecast, account: BankAccount, skipped: List[str]) -> ForecastResponse:
    data = asdict(forecast)

    return ForecastResponse(
        account_id=account.id,
        currency=account.currency,
        skipped_invoices=skipped,
        **data,
    )
