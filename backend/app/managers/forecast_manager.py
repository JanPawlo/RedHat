from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.const.action import ACTION_STATUSES_AFFECTING_FORECAST
from app.const.company import DEFAULT_MIN_SAFETY_BUFFER, MIN_SAFETY_BUFFER_KEY
from app.const.forecast import (
    CASH_CHANGES_KEY,
    CHANGE_AMOUNT_KEY,
    CHANGE_DAY_OFFSET_KEY,
    CHANGE_LABEL_KEY,
    FORECAST_HORIZON_DEFAULT_DAYS,
    FORECAST_HORIZON_MAX_DAYS,
    FORECAST_HORIZON_MIN_DAYS,
    FORECAST_HORIZON_SETTING_KEY,
    FORECAST_INVOICE_TYPES,
    INVOICE_TYPE_REVENUE,
    SCENARIO_BASE,
)
from app.managers.account_manager import get_account
from app.managers.action_manager import get_action
from app.models.account import BankAccount
from app.models.action import AgentAction
from app.models.company import CompanyProfile
from app.models.invoice import Invoice
from app.models.transaction import Transaction
from app.schemas.forecast import (
    AppliedDecisionResponse,
    CashChangeRequest,
    ForecastResponse,
    PlannedChangeResponse,
    ScenarioResponse,
    SimulationResponse,
)
from app.services.forecast_engine import (
    CashChange,
    CashRecord,
    Forecast,
    ForecastInputs,
    OpenInvoice,
    SimulationResult,
    build_forecast,
    simulate,
)


class ForecastActionNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class _Decision:
    action: AgentAction
    changes: Tuple[CashChange, ...]


async def get_forecast(db: AsyncSession, account_id: Optional[UUID], horizon_days: Optional[int]) -> Optional[ForecastResponse]:
    """Forecast without decisions ('do nothing') plus the base scenario after the approved cards."""
    account = await _resolve_account(db, account_id)
    if not account:
        return None

    inputs, skipped = await _load_inputs(db, account, horizon_days)
    decisions = await _approved_decisions(db, inputs.as_of)

    response = _to_response(build_forecast(inputs), account, skipped, decisions)

    planned = _all_changes(decisions)
    if planned:
        after = build_forecast(inputs, planned)
        response.after_decisions = ScenarioResponse(**asdict(after.scenarios[SCENARIO_BASE]))
        response.after_decisions_confidence = after.confidence

    return response


async def simulate_forecast(
    db: AsyncSession,
    account_id: Optional[UUID],
    horizon_days: Optional[int],
    changes: Sequence[CashChangeRequest],
) -> Optional[SimulationResponse]:
    """'What if' on top of the approved cards."""
    account = await _resolve_account(db, account_id)
    if not account:
        return None

    inputs, skipped = await _load_inputs(db, account, horizon_days)
    decisions = await _approved_decisions(db, inputs.as_of)

    new_changes = [CashChange(change.on_date, change.amount, change.label) for change in changes]
    result = simulate(inputs, new_changes, _all_changes(decisions))

    return _to_simulation_response(result, account, skipped, decisions)


async def preview_action(
    db: AsyncSession,
    action_id: UUID,
    account_id: Optional[UUID],
    horizon_days: Optional[int],
) -> Optional[SimulationResponse]:
    """Forecast before and after approving one card (other approved cards stay in both)."""
    action = await get_action(db, action_id)
    if not action:
        raise ForecastActionNotFoundError()

    account = await _resolve_account(db, account_id)
    if not account:
        return None

    inputs, skipped = await _load_inputs(db, account, horizon_days)
    others = [decision for decision in await _approved_decisions(db, inputs.as_of) if decision.action.id != action.id]

    card_changes = _card_changes(action, inputs.as_of)
    result = simulate(inputs, card_changes, _all_changes(others))

    return _to_simulation_response(result, account, skipped, others)


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


async def _approved_decisions(db: AsyncSession, as_of: date) -> List[_Decision]:
    query = select(AgentAction).where(
        AgentAction.status.in_(ACTION_STATUSES_AFFECTING_FORECAST)
    ).order_by(AgentAction.created_at)

    decisions: List[_Decision] = []
    for action in (await db.execute(query)).scalars().all():
        changes = _card_changes(action, as_of)
        if changes:
            decisions.append(_Decision(action=action, changes=changes))

    return decisions


def _card_changes(action: AgentAction, as_of: date) -> Tuple[CashChange, ...]:
    raw_changes = (action.impact_simulation or {}).get(CASH_CHANGES_KEY)
    if not isinstance(raw_changes, list):
        return ()

    changes = (_parse_change(raw, as_of, action.title) for raw in raw_changes)
    return tuple(change for change in changes if change)


def _parse_change(raw: Any, as_of: date, default_label: str) -> Optional[CashChange]:
    if not isinstance(raw, dict) or not isinstance(raw.get(CHANGE_DAY_OFFSET_KEY), int):
        return None

    try:
        amount = Decimal(str(raw.get(CHANGE_AMOUNT_KEY)))
    except InvalidOperation:
        return None
    if not amount.is_finite():
        return None

    on_date = as_of + timedelta(days=raw[CHANGE_DAY_OFFSET_KEY])
    return CashChange(on_date=on_date, amount=amount, label=str(raw.get(CHANGE_LABEL_KEY) or default_label))


def _all_changes(decisions: Sequence[_Decision]) -> List[CashChange]:
    return [change for decision in decisions for change in decision.changes]


def _applied(decisions: Sequence[_Decision]) -> List[AppliedDecisionResponse]:
    return [
        AppliedDecisionResponse(
            action_id=decision.action.id,
            title=decision.action.title,
            status=decision.action.status,
            changes=[PlannedChangeResponse(**asdict(change)) for change in decision.changes],
        )
        for decision in decisions
    ]


def _to_response(
    forecast: Forecast,
    account: BankAccount,
    skipped: List[str],
    decisions: Sequence[_Decision],
) -> ForecastResponse:
    data: Dict[str, Any] = asdict(forecast)

    return ForecastResponse(
        account_id=account.id,
        currency=account.currency,
        skipped_invoices=skipped,
        decisions_applied=_applied(decisions),
        **data,
    )


def _to_simulation_response(
    result: SimulationResult,
    account: BankAccount,
    skipped: List[str],
    decisions: Sequence[_Decision],
) -> SimulationResponse:
    return SimulationResponse(
        baseline=_to_response(result.baseline, account, skipped, decisions),
        simulated=_to_response(result.simulated, account, skipped, decisions),
        lowest_balance_change=result.lowest_balance_change,
    )
