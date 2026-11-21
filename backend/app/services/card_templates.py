"""
Card templates: decision scenarios pre-defined by developers.

A template finds where it applies (`detect`) and what each candidate does to the cash (`CashChange`s). It never
writes final wording itself: it hands named `slots` (already formatted numbers, dates and names) to the AI writer,
together with a brief, the fields to write and a fixed fallback text. Everything here is deterministic and has no
database or model access, so each template can be unit-tested with a small hand-made context.

Adding a template: write a `detect_*` function and register a `CardTemplate` in `REGISTRY` (checklist in
memory/spec/szablony-kart.md).
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from app.const.card_templates import (
    AMOUNT_STEP,
    BANK_DECIDES_PHRASES,
    CERTAINTY_BANK,
    CERTAINTY_COUNTERPARTY,
    CERTAINTY_OWN,
    COLLECTION_DISCOUNT_PERCENT,
    COLLECTION_PROMISE_DAYS,
    COLLECTION_STEPS,
    CREDIT_PRODUCTS,
    CREDIT_SAFETY_MARGIN,
    DAYS_PER_YEAR,
    DELAY_MAX_DAYS,
    DELAY_SEARCH_STEP_DAYS,
    DEPOSIT_MIN_FREE_CASH,
    DEPOSIT_SHARE_OF_FREE_CASH,
    DEPOSIT_TERM_DAYS,
    DEPOSIT_YEARLY_RATE,
    EXTENSION_DAYS_LANDLORD,
    EXTENSION_DAYS_SUPPLIER,
    EXTENSION_WINDOW_AFTER_DAYS,
    EXTENSION_WINDOW_BEFORE_DAYS,
    GOAL_CLOSE_GAP,
    GOAL_SAVE_MONEY,
    GOAL_USE_FREE_CASH,
    LANDLORD_CATEGORIES,
    LOCKED_MONEY_PHRASES,
    NEEDS_AGREEMENT_PHRASES,
    PROTECTED_CATEGORIES,
    PROTECTED_COUNTERPARTY_MARKERS,
    RELIABLE_COUNTERPARTY_MIN_PAYMENTS,
    RISK_LOW,
    RISK_MEDIUM,
    RISK_NONE,
    SUBSCRIPTION_CATEGORIES,
    SUBSCRIPTION_MARKERS,
    SUBSCRIPTION_MAX_MONTHLY,
    SUBSCRIPTION_NOTICE_DAYS,
    TEMPLATE_CANCEL_SUBSCRIPTION,
    TEMPLATE_COLLECT_OVERDUE,
    TEMPLATE_DELAY_INVESTMENT,
    TEMPLATE_EARLY_DISCOUNT,
    TEMPLATE_NEGOTIATE_EXTENSION,
    TEMPLATE_TAKE_CREDIT,
    TEMPLATE_TERM_DEPOSIT,
)
from app.const.forecast import SCENARIO_BASE, SCENARIO_PESSIMISTIC
from app.services.forecast_engine import (
    CashChange,
    Forecast,
    ForecastInputs,
    Indicators,
    RecurringPayment,
    SimulationResult,
    recurring_dates,
    simulate,
)

CENT = Decimal("0.01")
HUNDRED = Decimal("100")
ZERO = Decimal("0")
CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£"}


# ---------------------------------------------------------------- formatting (slots are always strings)

def money(amount: Decimal, currency: str) -> str:
    symbol = CURRENCY_SYMBOLS.get(currency)
    value = f"{abs(amount):,.0f}"
    sign = "-" if amount < 0 else ""
    return f"{sign}{symbol}{value}" if symbol else f"{sign}{value} {currency}"


def day_month(day: date) -> str:
    return f"{day.day} {day.strftime('%b')}"


def percent(value: Decimal) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{text}%"


def round_up(amount: Decimal, step: Decimal) -> Decimal:
    return (amount / step).to_integral_value(rounding=ROUND_CEILING) * step


def round_down(amount: Decimal, step: Decimal) -> Decimal:
    return (amount / step).to_integral_value(rounding=ROUND_FLOOR) * step


def _contains_marker(text: str, markers: Sequence[str]) -> bool:
    words = f" {''.join(ch if ch.isalnum() else ' ' for ch in text.lower())} "
    return any(f" {marker} " in words or (" " in marker and marker in text.lower()) for marker in markers)


# ---------------------------------------------------------------- inputs a template can read

@dataclass(frozen=True)
class InvoiceView:
    number: str
    counterparty: str
    is_revenue: bool
    amount: Decimal  # gross, positive
    currency: str
    issue_date: date
    due_date: date
    early_discount_percent: Optional[Decimal] = None
    early_discount_days: Optional[int] = None


@dataclass(frozen=True)
class LatePayerView:
    counterparty: str
    invoice_number: str
    amount: Decimal
    due_date: date
    expected_date: date
    typical_delay_days: int
    paid_invoices_seen: int


@dataclass(frozen=True)
class PlannedExpense:
    label: str
    amount: Decimal  # positive
    on_date: date
    movable: bool = True


@dataclass(frozen=True)
class TemplateContext:
    """Everything templates may read. Built by the card manager from the database and the forecast engine."""

    inputs: ForecastInputs
    planned: Tuple[CashChange, ...]  # approved decisions + planned expenses, already in `baseline`
    baseline: Forecast
    currency: str
    owner_name: str = "The owner"
    company_name: str = ""
    invoices: Tuple[InvoiceView, ...] = ()
    late_payers: Tuple[LatePayerView, ...] = ()
    payment_counts: Dict[str, int] = field(default_factory=dict)
    planned_expenses: Tuple[PlannedExpense, ...] = ()

    @property
    def as_of(self) -> date:
        return self.inputs.as_of

    @property
    def last_day(self) -> date:
        return self.inputs.as_of + timedelta(days=self.inputs.horizon_days)

    @property
    def buffer(self) -> Decimal:
        return self.inputs.safety_buffer

    @property
    def base(self) -> Indicators:
        return self.baseline.scenarios[SCENARIO_BASE].indicators

    @property
    def pessimistic(self) -> Indicators:
        return self.baseline.scenarios[SCENARIO_PESSIMISTIC].indicators

    @property
    def breach_date(self) -> Optional[date]:
        return self.base.first_below_buffer_date or self.pessimistic.first_below_buffer_date

    def simulate(self, changes: Sequence[CashChange]) -> SimulationResult:
        return simulate(self.inputs, list(changes), list(self.planned))

    def m(self, amount: Decimal) -> str:
        return money(amount, self.currency)

    def gap_slots(self) -> Dict[str, str]:
        """Slots every gap card can quote: when, how low, and the minimum the owner wants to keep."""
        return {
            "gap_date": day_month(self.breach_date) if self.breach_date else "",
            "lowest_balance": self.m(self.base.lowest_balance),
            "lowest_date": day_month(self.base.lowest_balance_date),
            "minimum_balance": self.m(self.buffer),
        }


# ---------------------------------------------------------------- template contract

@dataclass(frozen=True)
class EngineInput:
    """One piece of data a template takes from the math engine (or the database). `available=False` = engine gap."""

    name: str
    source: str
    available: bool = True
    gap: str = ""


@dataclass(frozen=True)
class Traits:
    certainty: str
    relationship_risk: str
    reversible: bool
    effort: str


@dataclass(frozen=True)
class Guardrails:
    autonomy_label: str = "Requires approval"
    hold_to_confirm_above: Decimal = Decimal("10000")
    must_mention: Tuple[str, ...] = ()  # slot keys every generated card must show (in any field)
    title_must_mention: Tuple[str, ...] = ()  # slot keys the title must show
    required_phrases: Tuple[Tuple[str, ...], ...] = ()  # each group: at least one phrase in proposal + explanation
    bank_product: bool = False  # card is a bank product: the UI shows the "bank product · disclosed" note
    extra_forbidden: Tuple[str, ...] = ()
    never_when: str = ""  # documented hard limit, enforced in `detect`


@dataclass(frozen=True)
class FallbackCopy:
    """Fixed text with {slot} placeholders, used when the model is down or its answer fails the guardrails."""

    title: str
    proposal: str
    explanation: str


@dataclass(frozen=True)
class MailTemplate:
    subject: str
    lines: Tuple[str, ...]


@dataclass(frozen=True)
class CardTemplate:
    key: str
    version: int
    goals: Tuple[str, ...]
    agent: str
    name: str
    brief: str  # what the card is about, for the model
    engine_inputs: Tuple[EngineInput, ...]
    traits: Traits
    guardrails: Guardrails
    right_label: str
    left_label: str
    questions: Tuple[str, ...]
    fallback: FallbackCopy
    detect: Callable[["TemplateContext"], List["Candidate"]]
    mail: Optional[MailTemplate] = None
    you_do: str = ""  # what the owner still does outside the app after approving ({slot} placeholders)
    max_cards: int = 2  # at most this many candidates of the template reach the deck
    allow_zero_effect: bool = False  # keep a candidate even if it does not move the lowest balance


@dataclass
class Candidate:
    template_key: str
    source_type: str
    source_id: str
    changes: Tuple[CashChange, ...]
    slots: Dict[str, str]
    amount: Decimal
    cost: Decimal = ZERO
    relationship_risk: Optional[str] = None  # overrides the template trait
    counterparty: Optional[str] = None

    def dedupe_key(self, template: CardTemplate) -> str:
        return f"tmpl:{template.key}:v{template.version}:{self.source_type}:{self.source_id}"[:160]


# ---------------------------------------------------------------- helpers shared by templates

def _protected(name: str, category: str = "") -> bool:
    return category.lower() in PROTECTED_CATEGORIES or _contains_marker(name, PROTECTED_COUNTERPARTY_MARKERS)


def _payments_seen(context: TemplateContext, name: str) -> int:
    return context.payment_counts.get(" ".join(name.lower().split()), 0)


def _day(context: TemplateContext, day: date) -> date:
    return max(day, context.as_of + timedelta(days=1))


def _within_horizon(context: TemplateContext, day: date) -> bool:
    return context.as_of < day <= context.last_day


def _extension_window(context: TemplateContext) -> Optional[Tuple[date, date]]:
    breach = context.breach_date
    if not breach:
        return None

    return breach - timedelta(days=EXTENSION_WINDOW_BEFORE_DAYS), breach + timedelta(days=EXTENSION_WINDOW_AFTER_DAYS)


# ---------------------------------------------------------------- 1. take credit

def detect_take_credit(context: TemplateContext) -> List[Candidate]:
    if not context.breach_date:
        return []

    shortfall = context.buffer - context.pessimistic.lowest_balance
    if shortfall <= ZERO:
        return []

    amount = round_up(shortfall * (1 + CREDIT_SAFETY_MARGIN), AMOUNT_STEP)
    draw_day = _day(context, context.breach_date - timedelta(days=1))
    recovery = _recovery_day(context, amount)
    candidates = [_credit_candidate(context, product, amount, draw_day, recovery) for product in CREDIT_PRODUCTS]
    return [candidate for candidate in candidates if candidate]


def _recovery_day(context: TemplateContext, amount: Decimal) -> Optional[date]:
    """First day after the lowest point on which the base balance could repay the credit and stay above the minimum."""
    lowest_day = context.base.lowest_balance_date
    for day in context.baseline.scenarios[SCENARIO_BASE].days:
        if day.day > lowest_day and day.balance >= context.buffer + amount:
            return day.day

    return None


def _credit_candidate(context, product, amount, draw_day, recovery) -> Optional[Candidate]:
    if not product["min_amount"] <= amount <= product["max_amount"]:
        return None

    if product["fixed_term_days"]:
        repay_day: Optional[date] = draw_day + timedelta(days=product["fixed_term_days"])
    else:
        repay_day = recovery

    interest_until = repay_day if repay_day and repay_day <= context.last_day else context.last_day
    days = max(1, (interest_until - draw_day).days)
    interest = (amount * product["yearly_rate"] * days / DAYS_PER_YEAR).quantize(CENT)
    fee = (amount * product["fee_percent"] / HUNDRED).quantize(CENT)

    changes = [CashChange(draw_day, amount, f"{product['name']} drawn")]
    if fee:
        changes.append(CashChange(draw_day, -fee, f"{product['name']} arrangement fee"))
    if repay_day and repay_day <= context.last_day:
        changes.append(CashChange(repay_day, -(amount + interest), f"{product['name']} repaid with interest"))
    else:
        changes.append(CashChange(context.last_day, -interest, f"{product['name']} interest so far"))

    repay_text = day_month(repay_day) if repay_day and repay_day <= context.last_day else f"after {day_month(context.last_day)}"
    return Candidate(
        template_key=TEMPLATE_TAKE_CREDIT,
        source_type="forecast",
        source_id=f"{context.as_of}:{product['key']}",
        changes=tuple(changes),
        amount=amount,
        cost=interest + fee,
        slots={
            **context.gap_slots(),
            "product_name": product["name"],
            "amount": context.m(amount),
            "draw_date": day_month(draw_day),
            "repay_date": repay_text,
            "days_used": str(days),
            "yearly_rate": percent(product["yearly_rate"] * HUNDRED),
            "interest": context.m(interest),
            "fee": context.m(fee),
            "total_cost": context.m(interest + fee),
            "worst_case_lowest": context.m(context.pessimistic.lowest_balance),
        },
    )


# ---------------------------------------------------------------- 2. negotiate a payment extension

def detect_negotiate_extension(context: TemplateContext) -> List[Candidate]:
    window = _extension_window(context)
    if not window:
        return []

    return [*_invoice_extensions(context, window), *_rent_extensions(context, window)]


def _invoice_extensions(context: TemplateContext, window: Tuple[date, date]) -> List[Candidate]:
    candidates: List[Candidate] = []
    for invoice in context.invoices:
        if invoice.is_revenue or invoice.currency != context.currency or invoice.early_discount_percent:
            continue
        if _protected(invoice.counterparty) or not window[0] <= invoice.due_date <= window[1]:
            continue

        payments = _payments_seen(context, invoice.counterparty)
        if payments < RELIABLE_COUNTERPARTY_MIN_PAYMENTS:
            continue

        new_due = invoice.due_date + timedelta(days=EXTENSION_DAYS_SUPPLIER)
        candidates.append(_extension_candidate(
            context, "invoice", invoice.number, invoice.counterparty, f"invoice {invoice.number}", invoice.amount,
            invoice.due_date, new_due, EXTENSION_DAYS_SUPPLIER, payments, RISK_MEDIUM,
        ))

    return candidates


def _rent_extensions(context: TemplateContext, window: Tuple[date, date]) -> List[Candidate]:
    candidates: List[Candidate] = []
    for payment in context.baseline.recurring:
        if payment.amount >= ZERO or payment.category.lower() not in LANDLORD_CATEGORIES:
            continue

        for due in recurring_dates(payment, context.as_of, context.last_day):
            if not window[0] <= due <= window[1]:
                continue

            new_due = due + timedelta(days=EXTENSION_DAYS_LANDLORD)
            candidates.append(_extension_candidate(
                context, "recurring", f"{payment.counterparty}:{due}", payment.counterparty,
                f"the {due.strftime('%B')} rent", -payment.amount, due, new_due, EXTENSION_DAYS_LANDLORD,
                payment.occurrences, RISK_LOW,
            ))

    return candidates


def _extension_candidate(context, source_type, source_id, counterparty, document, amount, due, new_due, days, payments, risk):
    return Candidate(
        template_key=TEMPLATE_NEGOTIATE_EXTENSION,
        source_type=source_type,
        source_id=source_id,
        changes=(
            CashChange(_day(context, due), amount, f"{counterparty} payment moved"),
            CashChange(new_due, -amount, f"{counterparty}, new payment date"),
        ),
        amount=amount,
        relationship_risk=risk,
        counterparty=counterparty,
        slots={
            **context.gap_slots(),
            "counterparty": counterparty,
            "document": document,
            "amount": context.m(amount),
            "due_date": day_month(due),
            "new_date": day_month(new_due),
            "extension_days": str(days),
            "payments_made": str(payments),
        },
    )


# ---------------------------------------------------------------- 3. collect overdue or late money

def detect_collect_overdue(context: TemplateContext) -> List[Candidate]:
    late = {payer.invoice_number: payer for payer in context.late_payers}
    candidates: List[Candidate] = []

    for invoice in context.invoices:
        if not invoice.is_revenue or invoice.currency != context.currency:
            continue

        days_overdue = (context.as_of - invoice.due_date).days
        payer = late.get(invoice.number)
        if days_overdue <= 0 and not payer:
            continue

        candidates.append(_collection_candidate(context, invoice, days_overdue, payer))

    return candidates


def _collection_step(days_overdue: int) -> Tuple[str, str, bool]:
    step = COLLECTION_STEPS[0]
    for candidate in COLLECTION_STEPS:
        if days_overdue >= candidate[0]:
            step = candidate

    return step[1], step[2], step[3]


def _collection_candidate(context, invoice: InvoiceView, days_overdue: int, payer: Optional[LatePayerView]) -> Candidate:
    step_key, step_label, with_discount = _collection_step(days_overdue)
    discount = (invoice.amount * COLLECTION_DISCOUNT_PERCENT / HUNDRED).quantize(CENT) if with_discount else ZERO
    promised = invoice.due_date if days_overdue <= 0 else context.as_of + timedelta(days=COLLECTION_PROMISE_DAYS)

    if payer:
        # The engine expects the money on due date + typical delay; collecting moves it to the promised date.
        changes: Tuple[CashChange, ...] = (
            CashChange(_day(context, promised), invoice.amount - discount, f"{invoice.counterparty} pays on time"),
            CashChange(_day(context, payer.expected_date), -invoice.amount, f"{invoice.counterparty} late payment no longer expected"),
        )
    else:
        # Engine gap: overdue sales invoices are already assumed paid on the first forecast day, so no visible effect.
        changes = ()

    slots = {
        "customer": invoice.counterparty,
        "invoice_number": invoice.number,
        "amount": context.m(invoice.amount),
        "due_date": day_month(invoice.due_date),
        "promised_date": day_month(promised),
        "step": step_label,
    }
    if days_overdue > 0:
        slots["days_overdue"] = str(days_overdue)
    if payer:
        slots["typical_delay_days"] = str(payer.typical_delay_days)
        slots["expected_date"] = day_month(payer.expected_date)
        slots["invoices_seen"] = str(payer.paid_invoices_seen)
    if discount:
        slots["discount_percent"] = percent(COLLECTION_DISCOUNT_PERCENT)
        slots["discount"] = context.m(discount)
        slots["amount_after_discount"] = context.m(invoice.amount - discount)
        slots["offer"] = f"They get {slots['discount_percent']} off ({slots['discount']}) if they pay by {slots['promised_date']}."
    if payer:
        slots["habit"] = f"They usually pay {payer.typical_delay_days} days late."

    return Candidate(
        template_key=TEMPLATE_COLLECT_OVERDUE,
        source_type="invoice",
        source_id=f"{invoice.number}:{step_key}",
        changes=changes,
        amount=invoice.amount,
        cost=discount,
        relationship_risk=RISK_MEDIUM if step_key in ("formal_demand", "payment_plan") else RISK_LOW,
        counterparty=invoice.counterparty,
        slots=slots,
    )


# ---------------------------------------------------------------- 4. cancel subscriptions

def _is_subscription(payment: RecurringPayment) -> bool:
    if _protected(payment.counterparty, payment.category):
        return False
    if payment.category.lower() in SUBSCRIPTION_CATEGORIES:
        return True

    return _contains_marker(payment.counterparty, SUBSCRIPTION_MARKERS)


def detect_cancel_subscription(context: TemplateContext) -> List[Candidate]:
    candidates: List[Candidate] = []
    effective = context.as_of + timedelta(days=SUBSCRIPTION_NOTICE_DAYS)

    for payment in context.baseline.recurring:
        monthly = -payment.amount / payment.interval_months
        if payment.amount >= ZERO or monthly > SUBSCRIPTION_MAX_MONTHLY or not _is_subscription(payment):
            continue

        avoided = recurring_dates(payment, effective, context.last_day)
        if not avoided:
            continue

        saving = -payment.amount * len(avoided)
        yearly = -payment.amount * 12 / payment.interval_months
        candidates.append(Candidate(
            template_key=TEMPLATE_CANCEL_SUBSCRIPTION,
            source_type="recurring",
            source_id=payment.counterparty,
            changes=tuple(CashChange(day, -payment.amount, f"{payment.counterparty} cancelled") for day in avoided),
            amount=-payment.amount,
            counterparty=payment.counterparty,
            slots={
                "service": payment.counterparty,
                "payment_amount": context.m(-payment.amount),
                "frequency": "every month" if payment.interval_months == 1 else f"every {payment.interval_months} months",
                "notice_days": str(SUBSCRIPTION_NOTICE_DAYS),
                "effective_date": day_month(effective),
                "payments_avoided": str(len(avoided)),
                "saving_in_forecast": context.m(saving),
                "saving_per_year": context.m(yearly),
            },
        ))

    return candidates


# ---------------------------------------------------------------- 5. delay a planned investment

def detect_delay_investment(context: TemplateContext) -> List[Candidate]:
    if not context.breach_date:
        return []

    candidates: List[Candidate] = []
    for expense in context.planned_expenses:
        if not expense.movable or not _within_horizon(context, expense.on_date):
            continue
        if expense.on_date > context.base.lowest_balance_date:
            continue

        new_day = _first_safe_day(context, expense)
        if not new_day:
            continue

        candidates.append(Candidate(
            template_key=TEMPLATE_DELAY_INVESTMENT,
            source_type="planned",
            source_id=f"{expense.label}:{expense.on_date}",
            changes=(
                CashChange(expense.on_date, expense.amount, f"{expense.label} moved"),
                CashChange(new_day, -expense.amount, f"{expense.label}, new date"),
            ),
            amount=expense.amount,
            slots={
                **context.gap_slots(),
                "item": expense.label,
                "amount": context.m(expense.amount),
                "planned_date": day_month(expense.on_date),
                "new_date": day_month(new_day),
                "delay_days": str((new_day - expense.on_date).days),
            },
        ))

    return candidates


def _first_safe_day(context: TemplateContext, expense: PlannedExpense) -> Optional[date]:
    """Earliest later date (weekly steps) on which the purchase no longer pushes the balance below the minimum."""
    best: Optional[Tuple[Decimal, date]] = None
    for offset in range(DELAY_SEARCH_STEP_DAYS, DELAY_MAX_DAYS + 1, DELAY_SEARCH_STEP_DAYS):
        new_day = expense.on_date + timedelta(days=offset)
        if new_day > context.last_day:
            break

        result = context.simulate([CashChange(expense.on_date, expense.amount, "moved"), CashChange(new_day, -expense.amount, "new date")])
        after = result.simulated.scenarios[SCENARIO_BASE].indicators
        if not after.first_below_buffer_date:
            return new_day
        if result.lowest_balance_change > ZERO and (not best or result.lowest_balance_change > best[0]):
            best = (result.lowest_balance_change, new_day)

    return best[1] if best else None


# ---------------------------------------------------------------- 6. early-payment discount (goal: save money)

def detect_early_discount(context: TemplateContext) -> List[Candidate]:
    candidates: List[Candidate] = []
    for invoice in context.invoices:
        if invoice.is_revenue or not invoice.early_discount_percent or not invoice.early_discount_days:
            continue
        if invoice.currency != context.currency:
            continue

        deadline = invoice.issue_date + timedelta(days=invoice.early_discount_days)
        if deadline <= context.as_of or deadline > invoice.due_date:
            continue

        discount = (invoice.amount * invoice.early_discount_percent / HUNDRED).quantize(CENT)
        payable = invoice.amount - discount
        candidates.append(Candidate(
            template_key=TEMPLATE_EARLY_DISCOUNT,
            source_type="invoice",
            source_id=invoice.number,
            changes=(
                CashChange(deadline, -payable, f"{invoice.counterparty} {invoice.number} paid early"),
                CashChange(_day(context, invoice.due_date), invoice.amount, f"{invoice.counterparty} {invoice.number} no longer due"),
            ),
            amount=payable,
            counterparty=invoice.counterparty,
            slots={
                "supplier": invoice.counterparty,
                "invoice_number": invoice.number,
                "invoice_amount": context.m(invoice.amount),
                "discount_percent": percent(invoice.early_discount_percent),
                "discount": context.m(discount),
                "pay_amount": context.m(payable),
                "pay_by": day_month(deadline),
                "due_date": day_month(invoice.due_date),
                "days_early": str((invoice.due_date - deadline).days),
            },
        ))

    return candidates


# ---------------------------------------------------------------- 7. term deposit (goal: use free cash)

def detect_term_deposit(context: TemplateContext) -> List[Candidate]:
    if context.breach_date:
        return []

    free_cash = context.pessimistic.lowest_balance - context.buffer
    if free_cash < DEPOSIT_MIN_FREE_CASH:
        return []

    amount = round_down(free_cash * DEPOSIT_SHARE_OF_FREE_CASH, AMOUNT_STEP)
    interest = (amount * DEPOSIT_YEARLY_RATE * DEPOSIT_TERM_DAYS / DAYS_PER_YEAR).quantize(CENT)
    start = context.as_of + timedelta(days=1)
    end = start + timedelta(days=DEPOSIT_TERM_DAYS)

    return [Candidate(
        template_key=TEMPLATE_TERM_DEPOSIT,
        source_type="forecast",
        source_id=str(context.as_of),
        changes=(CashChange(start, -amount, "Term deposit opened"), CashChange(end, amount + interest, "Term deposit returned with interest")),
        amount=amount,
        slots={
            "amount": context.m(amount),
            "term_days": str(DEPOSIT_TERM_DAYS),
            "yearly_rate": percent(DEPOSIT_YEARLY_RATE * HUNDRED),
            "interest": context.m(interest),
            "start_date": day_month(start),
            "end_date": day_month(end),
            "free_cash": context.m(free_cash),
            "stays_available": context.m(free_cash - amount),
            "minimum_balance": context.m(context.buffer),
        },
    )]


# ---------------------------------------------------------------- registry

FORECAST = "forecast_engine"
DATABASE = "database"

GAP_INPUTS = (
    EngineInput("Lowest balance and its date (base scenario)", f"{FORECAST}: Indicators.lowest_balance(_date)"),
    EngineInput("First day below the minimum balance", f"{FORECAST}: Indicators.first_below_buffer_date"),
    EngineInput("Worst-case lowest balance", f"{FORECAST}: pessimistic Indicators.lowest_balance"),
    EngineInput("Effect of the card (lowest balance before/after, confidence)", f"{FORECAST}: simulate()"),
)

REGISTRY: Tuple[CardTemplate, ...] = (
    CardTemplate(
        key=TEMPLATE_CANCEL_SUBSCRIPTION,
        version=1,
        goals=(GOAL_CLOSE_GAP, GOAL_SAVE_MONEY),
        agent="payables_optimizer",
        name="Cancel a subscription",
        brief=(
            "A recurring payment that looks like a subscription or service plan the business could cancel. The owner "
            "knows whether it is still used; ask, do not assume it is useless. Cancelling takes effect after the notice period."
        ),
        engine_inputs=(
            EngineInput("Recurring payments (counterparty, amount, interval, category)", f"{FORECAST}: Forecast.recurring"),
            EngineInput("Future dates of a recurring payment", f"{FORECAST}: recurring_dates()"),
            EngineInput("Is a recurring payment a subscription?", "transaction category / name markers", False,
                        "No subscription category: the statement parser never sets one; detection relies on name markers."),
            EngineInput("Notice period and contract end", DATABASE, False, "Not stored; a fixed 30 days is assumed."),
            EngineInput("Is the service still used?", DATABASE, False, "No usage data; the card asks the owner."),
        ),
        traits=Traits(certainty=CERTAINTY_OWN, relationship_risk=RISK_NONE, reversible=True, effort="low"),
        guardrails=Guardrails(
            must_mention=("service", "payment_amount", "saving_per_year"),
            title_must_mention=("service",),
            never_when="rent, salaries, taxes, social security, insurance, energy and loans are never offered for cancellation",
        ),
        right_label="Cancel it",
        left_label="Keep it",
        questions=("Do I still need it?", "When does the cancellation take effect?", "Explain it more simply"),
        fallback=FallbackCopy(
            title="Cancel the {service} subscription?",
            proposal="I will draft the cancellation for {service}. From {effective_date} you stop paying {payment_amount}.",
            explanation=(
                "You pay {service} {payment_amount} {frequency}, which is {saving_per_year} a year. "
                "If you no longer use it, cancelling saves {saving_in_forecast} in the coming weeks. Only you know if the business still needs it."
            ),
        ),
        detect=detect_cancel_subscription,
        you_do="Cancel it yourself in your {service} account or by writing to them; the app has no cancellation email for this yet.",
        max_cards=2,
    ),
    CardTemplate(
        key=TEMPLATE_COLLECT_OVERDUE,
        version=1,
        goals=(GOAL_CLOSE_GAP,),
        agent="receivables_agent",
        name="Collect money a customer owes",
        brief=(
            "A customer invoice is overdue or the customer usually pays late. The card proposes the next polite step "
            "(given in FACTS as 'step'). Stay respectful: the customer relationship matters."
        ),
        engine_inputs=(
            EngineInput("Open sales invoices", f"{DATABASE}: invoices (outgoing_revenue)"),
            EngineInput("Typical delay per customer and expected payment day", f"{FORECAST}: late_payers"),
            EngineInput("Effect of being paid on time", f"{FORECAST}: simulate()"),
            EngineInput("Overdue invoices in the forecast", f"{FORECAST}: _schedule_flows", False,
                        "Overdue sales invoices are assumed paid on the first forecast day, so collecting them shows no effect."),
            EngineInput("Reminders already sent (escalation history)", DATABASE, False, "Not stored; the step is chosen from days overdue only."),
            EngineInput("Probability that the customer pays", FORECAST, False, "Not modelled; collection is treated as certain once promised."),
        ),
        traits=Traits(certainty=CERTAINTY_COUNTERPARTY, relationship_risk=RISK_LOW, reversible=False, effort="low"),
        guardrails=Guardrails(
            autonomy_label="Email needs your OK",
            must_mention=("customer", "amount"),
            title_must_mention=("customer",),
            required_phrases=(NEEDS_AGREEMENT_PHRASES,),
            extra_forbidden=("lawyer", "court", "sue", "debt collector", "bailiff", "threat"),
            never_when="no legal threats; formal steps only after 30 days overdue",
        ),
        right_label="Send it",
        left_label="Wait",
        questions=("Write it more firmly", "Should I ask for prepayment next time?", "Explain it more simply"),
        fallback=FallbackCopy(
            title="Remind {customer} about invoice {invoice_number}?",
            proposal="I will send {customer} a {step} about {amount} and ask for payment by {promised_date}. {offer}",
            explanation=(
                "{customer} owes you {amount} for invoice {invoice_number}, due {due_date}. {habit} "
                "Being paid by {promised_date} brings the money in sooner. {customer} still has to pay, so it is not certain."
            ),
        ),
        detect=detect_collect_overdue,
        you_do="Nothing else unless {customer} does not pay by {promised_date}; then the next card suggests the next step.",
        mail=MailTemplate(
            subject="Invoice {invoice_number}",
            lines=(
                "Dear Sir or Madam,",
                "This is a {step} about invoice {invoice_number} for {amount}, due on {due_date}. "
                "We would be grateful for payment by {promised_date}.",
            ),
        ),
        max_cards=2,
        allow_zero_effect=True,
    ),
    CardTemplate(
        key=TEMPLATE_DELAY_INVESTMENT,
        version=1,
        goals=(GOAL_CLOSE_GAP,),
        agent="liquidity_guard",
        name="Delay a planned purchase",
        brief="A planned purchase (equipment, renovation) falls in the weeks when cash is tight. Moving it a little later avoids the low point.",
        engine_inputs=(
            *GAP_INPUTS,
            EngineInput("Planned purchases with dates", f"{DATABASE}: company settings 'planned_expenses'", False,
                        "Stopgap: read from company settings JSON; needs a proper table and an owner form or chat input."),
            EngineInput("Cost of delaying (lost revenue, price changes)", FORECAST, False, "Not modelled; the card says only the date changes."),
        ),
        traits=Traits(certainty=CERTAINTY_OWN, relationship_risk=RISK_NONE, reversible=True, effort="low"),
        guardrails=Guardrails(
            must_mention=("item", "amount", "new_date"),
            title_must_mention=("item",),
            never_when="only purchases the owner marked as movable",
        ),
        right_label="Move it",
        left_label="Keep the date",
        questions=("What if I buy it as planned?", "Could I lease it instead?", "Explain it more simply"),
        fallback=FallbackCopy(
            title="Move the {item} purchase to {new_date}?",
            proposal="Buy the {item} for {amount} on {new_date} instead of {planned_date}.",
            explanation=(
                "Your balance drops to {lowest_balance} on {lowest_date}, below the {minimum_balance} you want to keep. "
                "If you buy the {item} on {new_date} instead of {planned_date}, your lowest balance becomes {lowest_balance_with_card}. "
                "Nothing else changes."
            ),
        ),
        detect=detect_delay_investment,
        you_do="Move the order or delivery of the {item} to {new_date} with the seller yourself; the app does not contact anyone for this card.",
        max_cards=2,
    ),
    CardTemplate(
        key=TEMPLATE_NEGOTIATE_EXTENSION,
        version=1,
        goals=(GOAL_CLOSE_GAP,),
        agent="payables_optimizer",
        name="Ask for more time to pay",
        brief=(
            "A supplier invoice or the rent is due in the week cash is tight. The business has paid this company reliably, "
            "so asking politely for a short extension is reasonable. The other side has to agree."
        ),
        engine_inputs=(
            *GAP_INPUTS,
            EngineInput("Open supplier invoices", f"{DATABASE}: invoices (incoming_expense)"),
            EngineInput("Recurring payments such as rent", f"{FORECAST}: Forecast.recurring + recurring_dates()"),
            EngineInput("How many times the company was paid", f"{DATABASE}: outgoing transactions per counterparty"),
            EngineInput("Paid on time? (not just paid)", DATABASE, False, "Payments are counted, punctuality against due dates is not."),
        ),
        traits=Traits(certainty=CERTAINTY_COUNTERPARTY, relationship_risk=RISK_MEDIUM, reversible=True, effort="low"),
        guardrails=Guardrails(
            autonomy_label="Email needs your OK",
            must_mention=("counterparty", "amount", "new_date"),
            title_must_mention=("counterparty",),
            required_phrases=(NEEDS_AGREEMENT_PHRASES,),
            never_when="never for taxes, social security, health insurance or salaries",
        ),
        right_label="Ask for more time",
        left_label="Pay on time",
        questions=("What if they say no?", "Which payments cause the gap?", "Explain it more simply"),
        fallback=FallbackCopy(
            title="Ask {counterparty} to move {document} to {new_date}?",
            proposal="I will ask {counterparty} to move {document} ({amount}) from {due_date} to {new_date}.",
            explanation=(
                "Your balance drops to {lowest_balance} on {lowest_date}, below the {minimum_balance} you want to keep. "
                "If you pay {amount} on {new_date} instead of {due_date}, your lowest balance becomes {lowest_balance_with_card}. "
                "It costs nothing, but {counterparty} has to agree."
            ),
        ),
        detect=detect_negotiate_extension,
        you_do="Wait for the answer from {counterparty} (it arrives in Mail). Pay on {new_date} if they agree, or on {due_date} if they do not.",
        mail=MailTemplate(
            subject="Payment date: {document}",
            lines=(
                "Dear Sir or Madam,",
                "Could we move the payment of {document} ({amount}) from {due_date} to {new_date}? "
                "Thank you for the long cooperation.",
            ),
        ),
        max_cards=2,
    ),
    CardTemplate(
        key=TEMPLATE_TAKE_CREDIT,
        version=1,
        goals=(GOAL_CLOSE_GAP,),
        agent="liquidity_guard",
        name="Borrow to bridge the gap",
        brief=(
            "Cash falls below the minimum the owner wants to keep. A bank credit bridges the gap. It is a bank product "
            "that costs money: state the total cost honestly and remind that the bank decides."
        ),
        engine_inputs=(
            *GAP_INPUTS,
            EngineInput("Day the balance recovers enough to repay", f"{FORECAST}: base scenario days"),
            EngineInput("Bank products and their conditions", "const/card_templates.py CREDIT_PRODUCTS", False,
                        "Demo assumptions, not real Commerzbank conditions; no product API."),
            EngineInput("Interest charged only on the amount actually used", FORECAST, False,
                        "Interest is charged on the full amount for the whole period: an upper bound for overdrafts."),
            EngineInput("Current credit limit of the account", f"{DATABASE}: bank_accounts.overdraft_limit", False,
                        "Stored but not used by the engine: the forecast ignores an existing limit."),
        ),
        traits=Traits(certainty=CERTAINTY_BANK, relationship_risk=RISK_NONE, reversible=True, effort="medium"),
        guardrails=Guardrails(
            hold_to_confirm_above=Decimal("0"),
            must_mention=("amount", "total_cost"),
            title_must_mention=("amount",),
            required_phrases=(BANK_DECIDES_PHRASES,),
            bank_product=True,
            extra_forbidden=("approved", "approval is certain", "cheapest on the market"),
            never_when="only when cash falls below the minimum; amount sized to the worst case plus a margin",
        ),
        right_label="Request it",
        left_label="Not now",
        questions=("What does it cost in total?", "What are the other options?", "Explain it more simply"),
        fallback=FallbackCopy(
            title="Arrange a {amount} {product_name} before {gap_date}?",
            proposal="I will prepare a request for a {amount} {product_name} from {draw_date}. The bank decides.",
            explanation=(
                "Your balance drops to {lowest_balance} on {lowest_date}, below the {minimum_balance} you want to keep. "
                "With {amount} from the bank, your lowest balance becomes {lowest_balance_with_card}. "
                "It costs about {total_cost} in interest and fees."
            ),
        ),
        detect=detect_take_credit,
        you_do="The bank decides. If it agrees, you sign the agreement with the bank; nothing is borrowed before that.",
        mail=MailTemplate(
            subject="Request: {product_name}",
            lines=(
                "Dear Sir or Madam,",
                "We would like to discuss a {amount} {product_name} from {draw_date}, to cover a short gap in our cash in {gap_date}.",
            ),
        ),
        max_cards=1,
    ),
    CardTemplate(
        key=TEMPLATE_EARLY_DISCOUNT,
        version=1,
        goals=(GOAL_SAVE_MONEY,),
        agent="payables_optimizer",
        name="Pay early for a discount",
        brief="A supplier gives a discount for paying before a date. Paying early saves money but the cash leaves sooner.",
        engine_inputs=(
            EngineInput("Open supplier invoices with early-payment terms", f"{DATABASE}: invoices.early_discount_*"),
            EngineInput("Effect of paying early on the lowest balance", f"{FORECAST}: simulate()"),
        ),
        traits=Traits(certainty=CERTAINTY_OWN, relationship_risk=RISK_NONE, reversible=False, effort="low"),
        guardrails=Guardrails(
            must_mention=("supplier", "discount", "pay_by"),
            title_must_mention=("discount",),
            never_when="only while the discount deadline is in the future",
        ),
        right_label="Pay early",
        left_label="Pay on due date",
        questions=("Can I afford to pay now?", "Is the supplier reliable?", "Explain it more simply"),
        fallback=FallbackCopy(
            title="Pay {supplier} early and save {discount}?",
            proposal="Pay {pay_amount} for invoice {invoice_number} by {pay_by} instead of {invoice_amount} on {due_date}.",
            explanation=(
                "{supplier} takes {discount_percent} off if you pay by {pay_by}, which saves {discount}. "
                "The money leaves your account {days_early} days earlier than needed."
            ),
        ),
        detect=detect_early_discount,
        you_do="Pay {pay_amount} for invoice {invoice_number} by {pay_by} in your online banking; the app does not send money.",
        mail=MailTemplate(
            subject="Early payment of {invoice_number}",
            lines=("Dear Sir or Madam,", "We will pay invoice {invoice_number} by {pay_by} and use the {discount_percent} early-payment discount."),
        ),
        max_cards=2,
    ),
    CardTemplate(
        key=TEMPLATE_TERM_DEPOSIT,
        version=1,
        goals=(GOAL_USE_FREE_CASH,),
        agent="investment_agent",
        name="Put spare cash on a deposit",
        brief="Even in a bad month the balance stays well above the minimum. Part of the spare cash can earn interest for a short time.",
        engine_inputs=(
            EngineInput("Worst-case lowest balance (free cash)", f"{FORECAST}: pessimistic Indicators"),
            EngineInput("Deposit rates", "const/card_templates.py", False, "Demo assumption (3% a year), no product API."),
            EngineInput("Tax reserve to keep aside", FORECAST, False, "Not modelled: spare cash may include money needed for tax."),
        ),
        traits=Traits(certainty=CERTAINTY_BANK, relationship_risk=RISK_NONE, reversible=False, effort="low"),
        guardrails=Guardrails(
            hold_to_confirm_above=Decimal("0"),
            must_mention=("amount", "term_days", "interest"),
            title_must_mention=("amount",),
            required_phrases=(LOCKED_MONEY_PHRASES,),
            bank_product=True,
            never_when="never when cash falls below the minimum in any scenario",
        ),
        right_label="Open the deposit",
        left_label="Keep it available",
        questions=("What if I need the money earlier?", "How much will I earn?", "Explain it more simply"),
        fallback=FallbackCopy(
            title="Place {amount} on a {term_days}-day deposit?",
            proposal="Put {amount} on a deposit from {start_date} to {end_date} at {yearly_rate} a year.",
            explanation=(
                "Even in a bad month you keep more than the {minimum_balance} you want. {amount} could earn about {interest} "
                "in {term_days} days, and {stays_available} stays available. The money is locked until {end_date}."
            ),
        ),
        detect=detect_term_deposit,
        you_do="Open the deposit in your online banking; the app does not move money.",
        max_cards=1,
    ),
)

TEMPLATES_BY_KEY: Dict[str, CardTemplate] = {template.key: template for template in REGISTRY}


def templates_for(goals: Sequence[str]) -> List[CardTemplate]:
    return [template for template in REGISTRY if any(goal in template.goals for goal in goals)]


def active_goals(context: TemplateContext) -> List[str]:
    goals = [GOAL_SAVE_MONEY]
    if context.breach_date:
        goals.insert(0, GOAL_CLOSE_GAP)
    elif context.pessimistic.lowest_balance - context.buffer >= DEPOSIT_MIN_FREE_CASH:
        goals.append(GOAL_USE_FREE_CASH)

    return goals


def after_approval(template: CardTemplate, slots: Dict[str, str]) -> Dict[str, object]:
    """What the app does and what the owner does after approving this card (facts for the "Ask why" chat)."""
    app_does = [
        "Saves your decision and updates the cash forecast on the dashboard.",
        "Nothing real happens by itself: no money moves and nothing is sent to the bank or another company (simulated).",
    ]
    if template.mail:
        to = slots.get("counterparty") or slots.get("customer") or slots.get("supplier") or "the Commerzbank relationship manager"
        app_does.append(f"Offers to schedule an email to {to} ('{fill(template.mail.subject, slots)}') for 16:00 today; you can edit or stop it in Mail.")
    else:
        app_does.append("This card has no email draft.")
    app_does.append("Offers a calendar reminder for tomorrow at 9:00.")
    app_does.append("You can undo the decision in History.")

    return {"the_app_does": app_does, "you_do_yourself": fill(template.you_do, slots) or "Nothing else."}


def fill(text: str, slots: Dict[str, str]) -> str:
    """Fallback text with slots filled in (a missing slot leaves the sentence readable)."""
    class _Slots(dict):
        def __missing__(self, key):
            return ""

    return " ".join(text.format_map(_Slots(slots)).split())


def engine_gap_report() -> List[Tuple[str, str, str]]:
    """(template, missing input, why it matters) for every input the engine does not provide yet."""
    return [
        (template.key, item.name, item.gap)
        for template in REGISTRY
        for item in template.engine_inputs
        if not item.available
    ]
