"""
Decision cards built from the forecast engine's numbers.

Generation follows the deterministic approach of the feature/card_backend branch (every card is linked
to a record, has a dedupe key, the LLM never picks actions or computes effects), but liquidity is checked
with the full forecast (recurring payments, revenue, open invoices) instead of invoices alone.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.const.action import ACTION_STATUS_PENDING, EXECUTION_MODE_SIMULATED
from app.const.cards import (
    AGENT_DISPLAY,
    AGENT_INVESTMENT,
    AGENT_LIQUIDITY,
    AGENT_PAYABLES,
    AGENT_RECEIVABLES,
    AUTONOMY_REQUIRES_APPROVAL,
    BAR_MAX_HEIGHT,
    BAR_MIN_HEIGHT,
    CARD_HORIZON_DAYS,
    CARD_SOURCES,
    CARD_WEEKS,
    CREDIT_LINE_STEP,
    CREDIT_LINE_YEARLY_RATE,
    DEFAULT_AGENT_DISPLAY,
    EXPLAIN_FALLBACK_MODEL,
    CONFIDENCE_METHOD,
    RESPONSE_SOURCE_FALLBACK,
    RESPONSE_SOURCE_GUARDRAIL,
    RESPONSE_SOURCE_MODEL,
    DEFER_DAYS,
    DEFER_WINDOW_AFTER_DAYS,
    DEFER_WINDOW_BEFORE_DAYS,
    DEPOSIT_MIN_FREE_CASH,
    DEPOSIT_SHARE_OF_FREE_CASH,
    DEPOSIT_TERM_DAYS,
    DEPOSIT_YEARLY_RATE,
    HOLD_TO_CONFIRM_ABOVE,
    INTEREST_DAYS,
    MAIL_KEY,
    MONTHS_PER_YEAR,
    NEXT_SUB_KEY,
    ON_TIME_DISCOUNT_PERCENT,
    PRIORITY_KEY,
    RELIABLE_SUPPLIER_MIN_PAYMENTS,
    RESULT_SUFFIX,
    SOURCE_FORECAST,
    SOURCE_INVOICE,
    SWIPE_LEFT_KEY,
    SWIPE_RIGHT_KEY,
    TAX_COUNTERPARTY_MARKERS,
)
from app.const.calendar import EVENT_FACTS_MEANING, SEASONAL_CARD_PREFIX, SEASONAL_CARD_REASON, SEASONAL_CAUSE_MIN_SHARE
from app.const.forecast import (
    CASH_CHANGES_KEY,
    CHANGE_AMOUNT_KEY,
    CHANGE_DAY_OFFSET_KEY,
    CHANGE_LABEL_KEY,
    SCENARIO_BASE,
    SCENARIO_PESSIMISTIC,
)
from app.const.llm import UNKNOWN_MODEL_NAME
from app.core.config import settings
from app.managers.action_manager import get_action
from app.managers.forecast_manager import ForecastContext, card_changes, load_context, preview_result
from app.schemas.action import ExplainActionResponse
from app.const.guardrails import GUARDRAIL_MODEL_NAME
from app.services.guardrails import GuardrailBlockedError
from app.services.llm import LLMUnavailableError, explain_action
from app.models.action import AgentAction
from app.models.invoice import Invoice
from app.models.transaction import Transaction
from app.services.calendar_events import EventEffect, event_facts
from app.services.forecast_engine import Forecast, ForecastDay, SimulationResult, build_forecast, confidence_grid, weekly_lows

CENT = Decimal("0.01")
HUNDRED = Decimal("100")
CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£"}


@dataclass
class CardDraft:
    dedupe_key: str
    source_type: str
    source_id: str
    agent_type: str
    recommended_action: str
    title: str
    reason: str
    explanation: str
    amount: Decimal
    right: str
    left: str
    next_sub: str
    changes: List[Dict[str, Any]]
    priority: int
    mail: Optional[Dict[str, Any]] = None
    facts: Dict[str, Any] = field(default_factory=dict)


def money(amount: Decimal, currency: str) -> str:
    symbol = CURRENCY_SYMBOLS.get(currency)
    value = f"{abs(amount):,.0f}"
    sign = "-" if amount < 0 else ""
    return f"{sign}{symbol}{value}" if symbol else f"{sign}{value} {currency}"


def short_date(day: date) -> str:
    return day.strftime("%d %b").lstrip("0")


def _offset(context: ForecastContext, day: date) -> int:
    return max(1, (day - context.inputs.as_of).days)


def _change(day_offset: int, amount: Decimal, label: str) -> Dict[str, Any]:
    return {CHANGE_DAY_OFFSET_KEY: day_offset, CHANGE_AMOUNT_KEY: str(amount.quantize(CENT)), CHANGE_LABEL_KEY: label}


def _round_up(amount: Decimal, step: Decimal) -> Decimal:
    return (amount / step).to_integral_value(rounding=ROUND_CEILING) * step


def _round_down(amount: Decimal, step: Decimal) -> Decimal:
    return (amount / step).to_integral_value(rounding=ROUND_FLOOR) * step


def _initials(name: str) -> str:
    return "".join(part[0] for part in name.split()[:2]).upper()


def _owner(context: ForecastContext) -> str:
    settings = context.company.settings if context.company else {}
    name = context.company.name if context.company else ""
    return f"{settings.get('owner_name', 'The owner')}, {name}".strip(", ")


def _biggest_outflows(days: Sequence[ForecastDay], start: date, end: date, currency: str, limit: int = 3) -> List[str]:
    drivers = [
        (driver.amount, driver.label, day.day)
        for day in days
        if start <= day.day <= end
        for driver in day.drivers
        if driver.amount < 0
    ]
    drivers.sort(key=lambda item: item[0])
    return [f"{label} {money(amount, currency)} ({short_date(day)})" for amount, label, day in drivers[:limit]]


async def reset_decisions(db: AsyncSession) -> int:
    """Set every decided card back to pending, so the demo deck starts full again."""
    query = update(AgentAction).where(AgentAction.status != ACTION_STATUS_PENDING).values(status=ACTION_STATUS_PENDING, user_feedback=None)
    result = await db.execute(query)
    return result.rowcount or 0


async def generate_cards(db: AsyncSession) -> Dict[str, Any]:
    """Create cards for the situations the engine finds; existing cards (same dedupe key) are kept."""
    context = await load_context(db, None, CARD_HORIZON_DAYS)
    if not context:
        return {"created": 0, "skipped": ["No primary bank account"]}

    baseline = build_forecast(context.inputs, context.planned_changes)
    open_expenses = await _open_expenses(db)
    supplier_payments = await _payment_counts(db, context)

    drafts: List[CardDraft] = [
        *_liquidity_card(context, baseline),
        *_early_discount_cards(context, open_expenses),
        *_defer_cards(context, baseline, open_expenses, supplier_payments),
        *_late_payer_cards(context),
        *_deposit_card(context, baseline),
    ]

    created = 0
    for draft in drafts:
        exists = await db.execute(select(AgentAction.id).where(AgentAction.dedupe_key == draft.dedupe_key).limit(1))
        if exists.first():
            continue

        db.add(_to_action(draft, context))
        created += 1

    await db.flush()
    return {"created": created, "skipped": []}


async def _open_expenses(db: AsyncSession) -> List[Invoice]:
    query = select(Invoice).where(Invoice.is_paid.is_(False), Invoice.invoice_type == "incoming_expense").order_by(Invoice.due_date)
    return list((await db.execute(query)).scalars().all())


async def _payment_counts(db: AsyncSession, context: ForecastContext) -> Dict[str, int]:
    query = select(func.lower(Transaction.counterparty_name), func.count(Transaction.id)).where(
        Transaction.account_id == context.account.id, Transaction.amount < 0
    ).group_by(func.lower(Transaction.counterparty_name))
    return {name: count for name, count in (await db.execute(query)).all() if name}


def _liquidity_card(context: ForecastContext, baseline: Forecast) -> List[CardDraft]:
    base = baseline.scenarios[SCENARIO_BASE]
    pessimistic = baseline.scenarios[SCENARIO_PESSIMISTIC].indicators
    breach = base.indicators.first_below_buffer_date or pessimistic.first_below_buffer_date
    if not breach:
        return []

    currency = context.account.currency
    buffer = context.inputs.safety_buffer
    lowest = base.indicators.lowest_balance
    amount = _round_up(buffer - pessimistic.lowest_balance, CREDIT_LINE_STEP)
    draw_offset = max(1, (breach - context.inputs.as_of).days - 1)
    draw_day = context.inputs.as_of + timedelta(days=draw_offset)
    interest = (amount * CREDIT_LINE_YEARLY_RATE / MONTHS_PER_YEAR).quantize(CENT)
    outflows = _biggest_outflows(base.days, breach - timedelta(days=7), base.indicators.lowest_balance_date, currency)
    event = _gap_event(baseline.events, base.indicators.lowest_balance_date, buffer - pessimistic.lowest_balance)

    return [CardDraft(
        dedupe_key=f"forecast:{context.inputs.as_of}:credit_line",
        source_type=SOURCE_FORECAST,
        source_id=str(context.inputs.as_of),
        agent_type=AGENT_LIQUIDITY,
        recommended_action="activate_credit_line",
        title=_seasonal_prefix(event) + f"Pre-activate a {money(amount, currency)} credit line before {short_date(breach)}?",
        reason=(
            f"The forecast drops below your {money(buffer, currency)} buffer on {short_date(breach)} and reaches "
            f"{money(lowest, currency)} on {short_date(base.indicators.lowest_balance_date)}."
            + _seasonal_reason(event, currency)
        ),
        explanation=(
            f"Biggest outflows that week: {'; '.join(outflows)}. Drawing {money(amount, currency)} on {short_date(draw_day)} "
            f"covers even the pessimistic scenario (lowest {money(pessimistic.lowest_balance, currency)}). "
            f"Interest is about {money(interest, currency)} per month."
        ),
        amount=amount,
        right=f"Activate {money(amount, currency)}",
        left="Not now",
        next_sub=f"Liquidity · covers the {short_date(breach)} gap",
        changes=[
            _change(draw_offset, amount, "Commerzbank credit line drawn"),
            _change(draw_offset + INTEREST_DAYS, -interest, "Credit line interest"),
        ],
        priority=10,
        facts={
            "breach_date": str(breach),
            "pessimistic_lowest": str(pessimistic.lowest_balance),
            "monthly_interest": str(interest),
            "seasonal_cause": event_facts([event])[0] if event else None,
        },
    )]


def _gap_event(events: Sequence[EventEffect], lowest_day: date, shortfall: Decimal) -> Optional[EventEffect]:
    """The calendar event before the lowest balance that removes a real part of the shortfall (not a single quiet holiday)."""
    threshold = shortfall * SEASONAL_CAUSE_MIN_SHARE
    before_low = [event for event in events if event.start <= lowest_day and -event.event_days_change >= threshold > 0]
    return min(before_low, key=lambda event: event.event_days_change, default=None)


def _seasonal_prefix(event: Optional[EventEffect]) -> str:
    return SEASONAL_CARD_PREFIX.format(event=event.name) if event else ""


def _seasonal_reason(event: Optional[EventEffect], currency: str) -> str:
    if not event:
        return ""

    return SEASONAL_CARD_REASON.format(
        event=event.name,
        start=short_date(event.start),
        end=short_date(event.end),
        percent=int((event.effect * HUNDRED).to_integral_value()),
        source=event.source,
        change=money(event.event_days_change, currency),
    )


def _early_discount_cards(context: ForecastContext, invoices: Sequence[Invoice]) -> List[CardDraft]:
    drafts: List[CardDraft] = []
    for invoice in invoices:
        if not invoice.early_discount_percent or not invoice.early_discount_days or invoice.currency != context.account.currency:
            continue

        deadline = invoice.issue_date + timedelta(days=invoice.early_discount_days)
        if deadline <= context.inputs.as_of or deadline > invoice.due_date:
            continue

        currency = invoice.currency
        discount = (invoice.gross_amount * invoice.early_discount_percent / HUNDRED).quantize(CENT)
        payable = invoice.gross_amount - discount
        drafts.append(CardDraft(
            dedupe_key=f"invoice:{invoice.id}:early_discount:v1",
            source_type=SOURCE_INVOICE,
            source_id=str(invoice.id),
            agent_type=AGENT_PAYABLES,
            recommended_action="pay_early_discount",
            title=f"Pay {invoice.counterparty_name} early and save {money(discount, currency)}?",
            reason=(
                f"Invoice {invoice.invoice_number} ({money(invoice.gross_amount, currency)}) gives "
                f"{invoice.early_discount_percent}% off if paid by {short_date(deadline)} instead of {short_date(invoice.due_date)}."
            ),
            explanation=(
                f"Paying {money(payable, currency)} on {short_date(deadline)} saves {money(discount, currency)} and moves "
                f"the payment out of the due-date week. The forecast checks whether cash stays above the buffer in between."
            ),
            amount=payable,
            right=f"Pay early, save {money(discount, currency)}",
            left="Pay on due date",
            next_sub=f"Payables · {invoice.early_discount_percent}% off until {short_date(deadline)}",
            changes=[
                _change(_offset(context, deadline), -payable, f"{invoice.counterparty_name} {invoice.invoice_number} paid early"),
                _change(_offset(context, invoice.due_date), invoice.gross_amount, f"{invoice.counterparty_name} {invoice.invoice_number} no longer due"),
            ],
            priority=30,
            mail=_mail(context, invoice.counterparty_name, f"Early payment of {invoice.invoice_number}", [
                "Dear Sir or Madam,",
                f"We will pay invoice {invoice.invoice_number} by {short_date(deadline)} and use the {invoice.early_discount_percent}% "
                f"early-payment discount. The transfer will be {money(payable, currency)}.",
            ]),
            facts={"invoice_number": invoice.invoice_number, "discount": str(discount), "deadline": str(deadline), "due_date": str(invoice.due_date)},
        ))

    return drafts


def _is_tax(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in TAX_COUNTERPARTY_MARKERS)


def _defer_cards(
    context: ForecastContext,
    baseline: Forecast,
    invoices: Sequence[Invoice],
    supplier_payments: Dict[str, int],
) -> List[CardDraft]:
    base = baseline.scenarios[SCENARIO_BASE].indicators
    breach = base.first_below_buffer_date
    if not breach:
        return []

    window_start = breach - timedelta(days=DEFER_WINDOW_BEFORE_DAYS)
    window_end = breach + timedelta(days=DEFER_WINDOW_AFTER_DAYS)
    drafts: List[CardDraft] = []

    for invoice in invoices:
        payments = supplier_payments.get(invoice.counterparty_name.lower(), 0)
        if invoice.early_discount_percent or _is_tax(invoice.counterparty_name) or payments < RELIABLE_SUPPLIER_MIN_PAYMENTS:
            continue
        if not window_start <= invoice.due_date <= window_end or invoice.currency != context.account.currency:
            continue

        currency = invoice.currency
        new_due = invoice.due_date + timedelta(days=DEFER_DAYS)
        drafts.append(CardDraft(
            dedupe_key=f"invoice:{invoice.id}:defer:v1",
            source_type=SOURCE_INVOICE,
            source_id=str(invoice.id),
            agent_type=AGENT_PAYABLES,
            recommended_action="ask_payment_extension",
            title=f"Ask {invoice.counterparty_name} to move {invoice.invoice_number} by {DEFER_DAYS} days?",
            reason=(
                f"{money(invoice.gross_amount, currency)} is due {short_date(invoice.due_date)}, in the week the balance "
                f"falls below the buffer ({short_date(breach)})."
            ),
            explanation=(
                f"You have paid {invoice.counterparty_name} {payments} times on time, so a {DEFER_DAYS}-day extension is a "
                f"reasonable request. The payment moves to {short_date(new_due)}, after the tight week."
            ),
            amount=invoice.gross_amount,
            right="Send the request",
            left="Pay on time",
            next_sub=f"Payables · moves {money(invoice.gross_amount, currency)} out of the gap",
            changes=[
                _change(_offset(context, invoice.due_date), invoice.gross_amount, f"{invoice.counterparty_name} invoice moved"),
                _change(_offset(context, new_due), -invoice.gross_amount, f"{invoice.counterparty_name}, new due date"),
            ],
            priority=20,
            mail=_mail(context, invoice.counterparty_name, f"Payment date of {invoice.invoice_number}", [
                "Dear Sir or Madam,",
                f"Could we move the payment of invoice {invoice.invoice_number} ({money(invoice.gross_amount, currency)}) "
                f"from {short_date(invoice.due_date)} to {short_date(new_due)}? Thank you for the long cooperation.",
            ]),
            facts={"invoice_number": invoice.invoice_number, "on_time_payments": payments, "new_due_date": str(new_due)},
        ))

    return drafts


def _late_payer_cards(context: ForecastContext) -> List[CardDraft]:
    drafts: List[CardDraft] = []
    for late in context.late_payers:
        currency = context.account.currency
        discount = (late.amount * ON_TIME_DISCOUNT_PERCENT / HUNDRED).quantize(CENT)
        drafts.append(CardDraft(
            dedupe_key=f"invoice:{late.invoice_number}:late_payer:v1",
            source_type=SOURCE_INVOICE,
            source_id=late.invoice_number,
            agent_type=AGENT_RECEIVABLES,
            recommended_action="offer_on_time_discount",
            title=f"{late.counterparty} pays {late.typical_delay_days} days late. Offer {ON_TIME_DISCOUNT_PERCENT}% for paying on time?",
            reason=(
                f"Invoice {late.invoice_number} ({money(late.amount, currency)}) is due {short_date(late.due_date)}, "
                f"but based on their last {late.paid_invoices_seen} invoices the engine expects the money on {short_date(late.expected_date)}."
            ),
            explanation=(
                f"A reminder with a {ON_TIME_DISCOUNT_PERCENT}% discount ({money(discount, currency)}) for paying by "
                f"{short_date(late.due_date)} brings {money(late.amount - discount, currency)} in {late.typical_delay_days} days earlier."
            ),
            amount=late.amount,
            right=f"Send reminder with {ON_TIME_DISCOUNT_PERCENT}% off",
            left="Wait for payment",
            next_sub=f"Collections · usually {late.typical_delay_days} days late",
            changes=[
                _change(_offset(context, late.due_date), late.amount - discount, f"{late.counterparty} pays on time (-{ON_TIME_DISCOUNT_PERCENT}%)"),
                _change(_offset(context, late.expected_date), -late.amount, f"{late.counterparty} late payment no longer expected"),
            ],
            priority=25,
            mail=_mail(context, late.counterparty, f"Invoice {late.invoice_number}: {ON_TIME_DISCOUNT_PERCENT}% off for paying on time", [
                "Dear Sir or Madam,",
                f"Invoice {late.invoice_number} for {money(late.amount, currency)} is due on {short_date(late.due_date)}. "
                f"If you pay by then, you can deduct {ON_TIME_DISCOUNT_PERCENT}% ({money(discount, currency)}).",
            ]),
            facts={"typical_delay_days": late.typical_delay_days, "paid_invoices_seen": late.paid_invoices_seen, "expected_date": str(late.expected_date)},
        ))

    return drafts


def _deposit_card(context: ForecastContext, baseline: Forecast) -> List[CardDraft]:
    pessimistic = baseline.scenarios[SCENARIO_PESSIMISTIC].indicators
    free_cash = pessimistic.lowest_balance - context.inputs.safety_buffer
    if free_cash < DEPOSIT_MIN_FREE_CASH:
        return []

    currency = context.account.currency
    amount = _round_down(free_cash * DEPOSIT_SHARE_OF_FREE_CASH, CREDIT_LINE_STEP)
    interest = (amount * DEPOSIT_YEARLY_RATE / MONTHS_PER_YEAR).quantize(CENT)

    return [CardDraft(
        dedupe_key=f"forecast:{context.inputs.as_of}:deposit",
        source_type=SOURCE_FORECAST,
        source_id=str(context.inputs.as_of),
        agent_type=AGENT_INVESTMENT,
        recommended_action="open_term_deposit",
        title=f"Put {money(amount, currency)} into a {DEPOSIT_TERM_DAYS}-day deposit?",
        reason=f"Even in the pessimistic scenario the balance stays {money(free_cash, currency)} above the buffer.",
        explanation=f"The deposit returns about {money(interest, currency)} of interest; {money(free_cash - amount, currency)} of the free cash stays liquid.",
        amount=amount,
        right="Open the deposit",
        left="Keep it liquid",
        next_sub=f"Investment · {money(free_cash, currency)} free cash",
        changes=[
            _change(1, -amount, "Term deposit opened"),
            _change(1 + DEPOSIT_TERM_DAYS, amount + interest, "Term deposit returned with interest"),
        ],
        priority=40,
        facts={"free_cash_pessimistic": str(free_cash), "interest": str(interest)},
    )]


def _mail(context: ForecastContext, to: str, subject: str, lines: List[str]) -> Dict[str, Any]:
    return {"to": to, "initials": _initials(to), "subject": subject, "body": [*lines, f"Kind regards,\n{_owner(context)}"]}


def _to_action(draft: CardDraft, context: ForecastContext) -> AgentAction:
    impact = {
        CASH_CHANGES_KEY: draft.changes,
        SWIPE_RIGHT_KEY: draft.right,
        SWIPE_LEFT_KEY: draft.left,
        NEXT_SUB_KEY: draft.next_sub,
        PRIORITY_KEY: draft.priority,
        "engine_facts": draft.facts,
        "calculation_source": "forecast_engine_v1",
    }
    if draft.mail:
        impact[MAIL_KEY] = draft.mail

    return AgentAction(
        title=draft.title,
        agent_type=draft.agent_type,
        trigger_reason=draft.reason,
        recommended_action=draft.recommended_action,
        target_amount=draft.amount,
        currency=context.account.currency,
        explanation=draft.explanation,
        impact_simulation=impact,
        status=ACTION_STATUS_PENDING,
        execution_mode=EXECUTION_MODE_SIMULATED,
        source_type=draft.source_type,
        source_id=draft.source_id,
        dedupe_key=draft.dedupe_key,
    )


async def list_ui_cards(db: AsyncSession) -> List[Dict[str, Any]]:
    """Pending cards in the frontend's DecisionCard format, with the engine's effect of each one."""
    context = await load_context(db, None, CARD_HORIZON_DAYS)
    if not context:
        return []

    query = select(AgentAction).where(AgentAction.status == ACTION_STATUS_PENDING).order_by(AgentAction.created_at)
    actions = list((await db.execute(query)).scalars().all())
    actions.sort(key=lambda action: (action.impact_simulation or {}).get(PRIORITY_KEY, 99))

    return [to_ui_card(action, context, preview_result(context, action)) for action in actions]


def _bars(lows: Tuple[Decimal, ...], scale: Decimal) -> List[int]:
    return [max(BAR_MIN_HEIGHT, int(low / scale * BAR_MAX_HEIGHT)) if scale > 0 else BAR_MIN_HEIGHT for low in lows]


def to_ui_card(action: AgentAction, context: ForecastContext, result: SimulationResult) -> Dict[str, Any]:
    impact = action.impact_simulation or {}
    currency = action.currency
    agent, category, icon, bank_product = AGENT_DISPLAY.get(action.agent_type, DEFAULT_AGENT_DISPLAY)

    before = result.baseline.scenarios[SCENARIO_BASE]
    after = result.simulated.scenarios[SCENARIO_BASE]
    change = result.lowest_balance_change
    breach_after = after.indicators.first_below_buffer_date
    says_yes = change > 0 and result.simulated.confidence >= result.baseline.confidence and not breach_after

    weeks = weekly_lows(before.days, CARD_WEEKS)
    weeks_after = weekly_lows(after.days, CARD_WEEKS)
    scale = max([*weeks, *weeks_after, context.inputs.safety_buffer, Decimal("1")])
    amount = action.target_amount or Decimal("0")

    return {
        "id": str(action.id),
        "backendId": str(action.id),
        "agent": agent,
        "category": category,
        "icon": icon,
        "bankProduct": bank_product,
        "autonomy": AUTONOMY_REQUIRES_APPROVAL,
        "title": action.title,
        "proposal": action.trigger_reason,
        "confidence": int((result.simulated.confidence * HUNDRED).to_integral_value()),
        "recommendation": "right" if says_yes else "left",
        "left": impact.get(SWIPE_LEFT_KEY, "Decline"),
        "right": impact.get(SWIPE_RIGHT_KEY, "Approve"),
        "protects": float(max(change, Decimal("0"))),
        "amount": float(amount),
        "resultLabel": f"{impact.get(SWIPE_RIGHT_KEY, action.title)}{RESULT_SUFFIX}",
        "holdToConfirm": amount > HOLD_TO_CONFIRM_ABOVE,
        "followUps": ["scheduleMail", "calendar"] if impact.get(MAIL_KEY) else ["calendar"],
        "mail": impact.get(MAIL_KEY),
        "next": {
            "sub": impact.get(NEXT_SUB_KEY, agent),
            "chip": f"{'+' if change >= 0 else ''}{money(change, currency)}",
            "tone": "green" if says_yes else "amber",
        },
        "back": {
            "description": action.explanation,
            "facts": [
                ["Lowest balance now", f"{money(before.indicators.lowest_balance, currency)} · {short_date(before.indicators.lowest_balance_date)}"],
                ["Lowest if approved", f"{money(after.indicators.lowest_balance, currency)} · {short_date(after.indicators.lowest_balance_date)}"],
                ["Safety buffer", money(context.inputs.safety_buffer, currency)],
                ["Buffer if approved", f"broken {short_date(breach_after)}" if breach_after else "holds"],
                ["Confidence", f"{int(result.baseline.confidence * HUNDRED)}% → {int(result.simulated.confidence * HUNDRED)}%"],
            ],
            "weeks": _bars(weeks, scale),
            "weeksIfApproved": _bars(weeks_after, scale),
            "bufferLevel": _bars((context.inputs.safety_buffer,), scale)[0],
            "sources": CARD_SOURCES,
            "questions": [
                "Where does the confidence come from?",
                "What if I do nothing?",
                "Which payments cause the gap?",
                "Explain it more simply",
            ],
        },
        "engine": {
            "lowest_before": str(before.indicators.lowest_balance),
            "lowest_after": str(after.indicators.lowest_balance),
            "lowest_change": str(change),
            "confidence_before": str(result.baseline.confidence),
            "confidence_after": str(result.simulated.confidence),
            "breach_after": str(breach_after) if breach_after else None,
        },
    }


async def explain_card(db: AsyncSession, action_id, question: str) -> Optional[ExplainActionResponse]:
    """The LLM explains the engine's facts for one card; without the model a deterministic answer is returned."""
    action = await get_action(db, action_id)
    if not action:
        return None

    context = await load_context(db, None, CARD_HORIZON_DAYS)
    facts = explain_facts(action, context) if context else {"card_front": _card_front(action)}

    try:
        answer = await explain_action(facts=facts, question=question)
        model, source = settings.MODEL_NAME or UNKNOWN_MODEL_NAME, RESPONSE_SOURCE_MODEL
    except GuardrailBlockedError as blocked:
        answer = blocked.refusal
        model, source = GUARDRAIL_MODEL_NAME, RESPONSE_SOURCE_GUARDRAIL
    except LLMUnavailableError:
        answer = fallback_answer(facts) or action.explanation
        model, source = EXPLAIN_FALLBACK_MODEL, RESPONSE_SOURCE_FALLBACK

    return ExplainActionResponse(
        action_id=action.id,
        model=model,
        question=question,
        answer=answer,
        facts_used=facts,
        response_source=source,
    )


def _card_front(action: AgentAction) -> Dict[str, Any]:
    impact = action.impact_simulation or {}
    return {"title": action.title, "proposal": action.trigger_reason, "recommended_choice": impact.get(SWIPE_RIGHT_KEY)}


def _percent(value: Decimal) -> int:
    return int((value * HUNDRED).to_integral_value())


def explain_facts(action: AgentAction, context: ForecastContext) -> Dict[str, Any]:
    currency = context.account.currency
    inputs = context.inputs
    own = card_changes(action, inputs.as_of)
    others = [change for decision in context.decisions if decision.action.id != action.id for change in decision.changes]

    result = preview_result(context, action)
    before = result.baseline.scenarios[SCENARIO_BASE]
    after = result.simulated.scenarios[SCENARIO_BASE]
    grid = confidence_grid(inputs, [*others, *own])
    model = result.baseline.revenue_model
    lowest_day = before.indicators.lowest_balance_date

    return {
        "card_front": _card_front(action),
        "engine": {
            "forecast_start": str(inputs.as_of),
            "balance_today": money(inputs.opening_balance, currency),
            "safety_buffer": money(inputs.safety_buffer, currency),
            "horizon_days": inputs.horizon_days,
            "lowest_balance_without_card": f"{money(before.indicators.lowest_balance, currency)} on {lowest_day}",
            "lowest_balance_with_card": f"{money(after.indicators.lowest_balance, currency)} on {after.indicators.lowest_balance_date}",
            "buffer_broken_without_card": str(before.indicators.first_below_buffer_date) if before.indicators.first_below_buffer_date else "never",
            "buffer_broken_with_card": str(after.indicators.first_below_buffer_date) if after.indicators.first_below_buffer_date else "never",
            "confidence_without_card_percent": _percent(result.baseline.confidence),
            "confidence_with_card_percent": _percent(result.simulated.confidence),
            "confidence_method": CONFIDENCE_METHOD.format(
                steps=len(grid), low=_percent(grid[0].revenue_factor), high=_percent(grid[-1].revenue_factor), days=inputs.horizon_days
            ),
            "revenue_scenarios_with_card": [
                {"revenue_level_percent": _percent(point.revenue_factor), "lowest_balance": money(point.lowest_balance, currency), "keeps_buffer": point.keeps_buffer}
                for point in grid
            ],
            "card_cash_changes": [{"date": str(change.on_date), "amount": money(change.amount, currency), "label": change.label} for change in own],
            "biggest_outflows_near_lowest": _biggest_outflows(before.days, lowest_day - timedelta(days=7), lowest_day, currency, 4),
            "recurring_payments": [
                f"{payment.counterparty}: {money(payment.amount, currency)} every {payment.interval_months} month(s) on day {payment.day_of_month}"
                for payment in sorted(result.baseline.recurring, key=lambda item: item.amount)[:6]
            ],
            "revenue_model": {
                "average_revenue_per_weekday_mon_to_sun": [money(value, currency) for value in model.weekday_inflow],
                "variable_costs_percent_of_revenue": _percent(model.variable_cost_ratio),
                "weekly_revenue_volatility_percent": _percent(model.volatility),
            },
            "late_payers": [
                f"{late.counterparty} pays {late.typical_delay_days} days late on average ({late.paid_invoices_seen} invoices)"
                for late in context.late_payers
            ],
            "calendar_events": event_facts(result.baseline.events),
            "calendar_events_meaning": EVENT_FACTS_MEANING,
        },
        "card_specific_facts": (action.impact_simulation or {}).get("engine_facts", {}),
    }


def fallback_answer(facts: Dict[str, Any]) -> Optional[str]:
    engine = facts.get("engine")
    if not engine:
        return None

    grid = engine["revenue_scenarios_with_card"]
    safe = sum(1 for point in grid if point["keeps_buffer"])
    return (
        f"Confidence {engine['confidence_with_card_percent']}% (without this decision {engine['confidence_without_card_percent']}%): "
        f"the engine tried {len(grid)} revenue levels from {grid[0]['revenue_level_percent']}% to {grid[-1]['revenue_level_percent']}% "
        f"of the expected revenue, and in {safe} of them the balance stays above the {engine['safety_buffer']} buffer. "
        f"Lowest balance: {engine['lowest_balance_without_card']} now, {engine['lowest_balance_with_card']} with this decision. "
        f"Buffer broken: {engine['buffer_broken_without_card']} now, {engine['buffer_broken_with_card']} with it."
    )
