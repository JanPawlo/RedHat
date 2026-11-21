from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from statistics import median
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.const.action import ACTION_STATUSES_AFFECTING_FORECAST
from app.const.calendar import COMPANY_EVENTS_SETTING_KEY
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
    HISTORY_DAYS,
    INVOICE_TYPE_REVENUE,
    LATE_PAYER_LABEL,
    LATE_PAYER_MIN_DELAY_DAYS,
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
    BalancePointResponse,
    CashChangeRequest,
    ForecastResponse,
    LatePayerResponse,
    PlannedChangeResponse,
    ScenarioResponse,
    SimulationResponse,
)
from app.services.calendar_events import EventOccurrence, calendar_occurrences, company_event_definitions
from app.services.forecast_engine import (
    CashChange,
    CashRecord,
    Forecast,
    ForecastInputs,
    OpenInvoice,
    SimulationResult,
    balance_history,
    build_forecast,
    simulate,
)


class ForecastActionNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class Decision:
    action: AgentAction
    changes: Tuple[CashChange, ...]


@dataclass(frozen=True)
class ForecastContext:
    """Everything the engine needs for one account, loaded once per request."""

    account: BankAccount
    company: Optional[CompanyProfile]
    inputs: ForecastInputs
    skipped_invoices: List[str]
    late_payers: List[LatePayerResponse]
    decisions: List[Decision]

    @property
    def planned_changes(self) -> List[CashChange]:
        return [change for decision in self.decisions for change in decision.changes]


async def load_context(db: AsyncSession, account_id: Optional[UUID], horizon_days: Optional[int]) -> Optional[ForecastContext]:
    account = await _resolve_account(db, account_id)
    if not account:
        return None

    company = await _company(db)
    as_of = await _as_of(db, account.id)
    history = await _history(db, account.id)
    invoices, skipped, late_payers = await _open_invoices(db, account)

    inputs = ForecastInputs(
        as_of=as_of,
        opening_balance=account.current_balance,
        safety_buffer=_safety_buffer(company),
        horizon_days=horizon_days or _default_horizon(company),
        history=history,
        invoices=invoices,
        events=_calendar(company, history, as_of),
    )
    decisions = await _approved_decisions(db, as_of)

    return ForecastContext(account, company, inputs, skipped, late_payers, decisions)


def _calendar(company: Optional[CompanyProfile], history: Sequence[CashRecord], as_of: date) -> Tuple[EventOccurrence, ...]:
    """Calendar events for the company's country and its own yearly events, from the first booking to the longest horizon."""
    first_year = min((record.booking_date for record in history), default=as_of).year
    last_year = (as_of + timedelta(days=FORECAST_HORIZON_MAX_DAYS)).year
    country = company.country if company else None
    own_events = company_event_definitions((company.settings or {}).get(COMPANY_EVENTS_SETTING_KEY)) if company else ()

    return calendar_occurrences(country, first_year, last_year, own_events)


async def get_forecast(db: AsyncSession, account_id: Optional[UUID], horizon_days: Optional[int]) -> Optional[ForecastResponse]:
    """Forecast without decisions ('do nothing') plus the base scenario after the approved cards."""
    context = await load_context(db, account_id, horizon_days)
    if not context:
        return None

    response = to_response(build_forecast(context.inputs), context)
    response.history = _history_points(context)

    if context.planned_changes:
        after = build_forecast(context.inputs, context.planned_changes)
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
    context = await load_context(db, account_id, horizon_days)
    if not context:
        return None

    new_changes = [CashChange(change.on_date, change.amount, change.label) for change in changes]
    result = simulate(context.inputs, new_changes, context.planned_changes)

    return to_simulation_response(result, context)


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

    context = await load_context(db, account_id, horizon_days)
    if not context:
        return None

    return to_simulation_response(preview_result(context, action), context)


def preview_result(context: ForecastContext, action: AgentAction) -> SimulationResult:
    others = [change for decision in context.decisions if decision.action.id != action.id for change in decision.changes]
    return simulate(context.inputs, card_changes(action, context.inputs.as_of), others)


def card_changes(action: AgentAction, as_of: date) -> Tuple[CashChange, ...]:
    raw_changes = (action.impact_simulation or {}).get(CASH_CHANGES_KEY)
    if not isinstance(raw_changes, list):
        return ()

    changes = (_parse_change(raw, as_of, action.title) for raw in raw_changes)
    return tuple(change for change in changes if change)


async def _resolve_account(db: AsyncSession, account_id: Optional[UUID]) -> Optional[BankAccount]:
    if account_id:
        return await get_account(db, account_id)

    query = select(BankAccount).where(BankAccount.is_primary.is_(True)).order_by(BankAccount.created_at).limit(1)
    return (await db.execute(query)).scalars().first()


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


def _normalize(name: str) -> str:
    return " ".join(name.lower().split())


async def _customer_delays(db: AsyncSession) -> Dict[str, Tuple[int, int]]:
    """Typical days late per customer from paid sales invoices: {customer: (median delay, invoices seen)}."""
    query = select(Invoice.counterparty_name, Invoice.due_date, Transaction.booking_date).join(
        Transaction, Invoice.paid_transaction_id == Transaction.id
    ).where(Invoice.invoice_type == INVOICE_TYPE_REVENUE, Invoice.is_paid.is_(True))

    delays: Dict[str, List[int]] = defaultdict(list)
    for counterparty, due_date, paid_on in (await db.execute(query)).all():
        delays[_normalize(counterparty)].append((paid_on - due_date).days)

    return {name: (int(median(values)), len(values)) for name, values in delays.items()}


async def _open_invoices(
    db: AsyncSession,
    account: BankAccount,
) -> Tuple[Tuple[OpenInvoice, ...], List[str], List[LatePayerResponse]]:
    query = select(Invoice).where(
        Invoice.is_paid.is_(False),
        Invoice.invoice_type.in_(FORECAST_INVOICE_TYPES),
        or_(Invoice.account_id == account.id, Invoice.account_id.is_(None)),
    ).order_by(Invoice.due_date)

    delays = await _customer_delays(db)
    invoices: List[OpenInvoice] = []
    skipped: List[str] = []
    late_payers: List[LatePayerResponse] = []

    for invoice in (await db.execute(query)).scalars().all():
        if invoice.currency != account.currency:
            skipped.append(invoice.invoice_number)
            continue

        late = _late_payer(invoice, delays)
        if late:
            late_payers.append(late)
        invoices.append(_to_open_invoice(invoice, late))

    return tuple(invoices), skipped, late_payers


def _late_payer(invoice: Invoice, delays: Dict[str, Tuple[int, int]]) -> Optional[LatePayerResponse]:
    if invoice.invoice_type != INVOICE_TYPE_REVENUE:
        return None

    delay, seen = delays.get(_normalize(invoice.counterparty_name), (0, 0))
    if delay < LATE_PAYER_MIN_DELAY_DAYS:
        return None

    return LatePayerResponse(
        counterparty=invoice.counterparty_name,
        invoice_number=invoice.invoice_number,
        amount=invoice.gross_amount,
        due_date=invoice.due_date,
        expected_date=invoice.due_date + timedelta(days=delay),
        typical_delay_days=delay,
        paid_invoices_seen=seen,
    )


def _to_open_invoice(invoice: Invoice, late: Optional[LatePayerResponse]) -> OpenInvoice:
    if late:
        return OpenInvoice(
            invoice_number=LATE_PAYER_LABEL.format(number=invoice.invoice_number, delay=late.typical_delay_days),
            counterparty=invoice.counterparty_name,
            due_date=late.expected_date,
            amount=invoice.gross_amount,
        )

    sign = Decimal("1") if invoice.invoice_type == INVOICE_TYPE_REVENUE else Decimal("-1")
    return OpenInvoice(
        invoice_number=invoice.invoice_number,
        counterparty=invoice.counterparty_name,
        due_date=invoice.due_date,
        amount=invoice.gross_amount * sign,
    )


async def _approved_decisions(db: AsyncSession, as_of: date) -> List[Decision]:
    query = select(AgentAction).where(
        AgentAction.status.in_(ACTION_STATUSES_AFFECTING_FORECAST)
    ).order_by(AgentAction.created_at)

    decisions: List[Decision] = []
    for action in (await db.execute(query)).scalars().all():
        changes = card_changes(action, as_of)
        if changes:
            decisions.append(Decision(action=action, changes=changes))

    return decisions


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


def _history_points(context: ForecastContext) -> List[BalancePointResponse]:
    points = balance_history(context.inputs.history, context.inputs.as_of, context.inputs.opening_balance, HISTORY_DAYS)
    return [BalancePointResponse(day=point.day, balance=point.balance) for point in points]


def _applied(decisions: Sequence[Decision]) -> List[AppliedDecisionResponse]:
    return [
        AppliedDecisionResponse(
            action_id=decision.action.id,
            title=decision.action.title,
            status=decision.action.status,
            changes=[PlannedChangeResponse(**asdict(change)) for change in decision.changes],
        )
        for decision in decisions
    ]


def to_response(forecast: Forecast, context: ForecastContext) -> ForecastResponse:
    data: Dict[str, Any] = asdict(forecast)

    return ForecastResponse(
        account_id=context.account.id,
        currency=context.account.currency,
        skipped_invoices=context.skipped_invoices,
        decisions_applied=_applied(context.decisions),
        late_payers=context.late_payers,
        **data,
    )


def to_simulation_response(result: SimulationResult, context: ForecastContext) -> SimulationResponse:
    return SimulationResponse(
        baseline=to_response(result.baseline, context),
        simulated=to_response(result.simulated, context),
        lowest_balance_change=result.lowest_balance_change,
    )
