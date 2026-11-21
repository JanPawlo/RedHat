"""
Deterministic cash forecast engine ('the engine calculates, the AI explains').

Pure functions without database access: the manager loads data, converts it into the
dataclasses below and passes them in. Every forecast number can be traced back to a
driver (expected revenue, variable costs, a recurring payment, an invoice or a change).
"""

import calendar
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from statistics import median, pstdev
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from app.const.forecast import (
    CONFIDENCE_GRID_STEPS,
    DAYS_PER_MONTH,
    DRIVER_EXPECTED_REVENUE,
    DRIVER_INVOICE,
    DRIVER_RECURRING,
    DRIVER_VARIABLE_COSTS,
    DRIVERS_PER_DAY_LIMIT,
    RECURRING_AMOUNT_TOLERANCE,
    RECURRING_INTERVALS_MONTHS,
    RECURRING_INVOICE_MATCH_DAYS,
    RECURRING_MIN_OCCURRENCES,
    RECURRING_STALE_GRACE_DAYS,
    REVENUE_LOOKBACK_DAYS,
    SCENARIO_BASE,
    SCENARIO_MAX_REVENUE_FACTOR,
    SCENARIO_MIN_REVENUE_FACTOR,
    SCENARIO_OPTIMISTIC,
    SCENARIO_PESSIMISTIC,
    SCENARIO_MIN_SPREAD,
    SCENARIO_VOLATILITY_MULTIPLIER,
    SEASONALITY_MIN_HISTORY_DAYS,
)

ZERO = Decimal("0")
ONE = Decimal("1")
CENT = Decimal("0.01")
FACTOR_PRECISION = Decimal("0.0001")
RUNWAY_PRECISION = Decimal("0.1")
RECURRING_INTERVAL_SHARE = Decimal("0.75")
WEEKDAYS = 7


@dataclass(frozen=True)
class CashRecord:
    """One booked bank transaction, amount signed in the account currency."""

    booking_date: date
    amount: Decimal
    counterparty: str = ""
    category: str = ""


@dataclass(frozen=True)
class OpenInvoice:
    """Unpaid invoice; amount is signed (+ money in, - money out)."""

    invoice_number: str
    counterparty: str
    due_date: date
    amount: Decimal


@dataclass(frozen=True)
class CashChange:
    """Extra cash movement used by 'what if' simulations (+ in, - out)."""

    on_date: date
    amount: Decimal
    label: str


@dataclass(frozen=True)
class RecurringPayment:
    counterparty: str
    category: str
    amount: Decimal
    interval_months: int
    day_of_month: int
    last_date: date
    occurrences: int


@dataclass(frozen=True)
class ForecastInputs:
    as_of: date
    opening_balance: Decimal
    safety_buffer: Decimal
    horizon_days: int
    history: Tuple[CashRecord, ...] = ()
    invoices: Tuple[OpenInvoice, ...] = ()


@dataclass(frozen=True)
class Driver:
    label: str
    amount: Decimal


@dataclass(frozen=True)
class ForecastDay:
    day: date
    balance: Decimal
    inflows: Decimal
    outflows: Decimal
    drivers: Tuple[Driver, ...]


@dataclass(frozen=True)
class Indicators:
    lowest_balance: Decimal
    lowest_balance_date: date
    first_below_buffer_date: Optional[date]
    first_below_zero_date: Optional[date]
    days_to_buffer_breach: Optional[int]
    runway_months: Optional[Decimal]
    free_cash: Decimal


@dataclass(frozen=True)
class ScenarioForecast:
    name: str
    revenue_factor: Decimal
    days: Tuple[ForecastDay, ...]
    indicators: Indicators


@dataclass(frozen=True)
class RevenueModel:
    weekday_inflow: Tuple[Decimal, ...]
    variable_cost_ratio: Decimal
    month_factors: Dict[int, Decimal]
    lookback_factor: Decimal
    volatility: Decimal


@dataclass(frozen=True)
class Forecast:
    as_of: date
    opening_balance: Decimal
    safety_buffer: Decimal
    horizon_days: int
    revenue_model: RevenueModel
    recurring: Tuple[RecurringPayment, ...]
    scenarios: Dict[str, ScenarioForecast]
    confidence: Decimal


@dataclass(frozen=True)
class SimulationResult:
    baseline: Forecast
    simulated: Forecast
    lowest_balance_change: Decimal


def build_forecast(inputs: ForecastInputs, changes: Sequence[CashChange] = ()) -> Forecast:
    """Forecast the daily balance in pessimistic, base and optimistic scenarios."""
    _ensure_horizon(inputs.horizon_days)
    history = _history_until(inputs.history, inputs.as_of)

    recurring, recurring_indexes = _detect_recurring(history, inputs.as_of)
    operating = [record for index, record in enumerate(history) if index not in recurring_indexes]
    model = build_revenue_model(operating, inputs.as_of)

    scheduled = _schedule_flows(inputs, recurring, changes)
    factors = _scenario_factors(model.volatility)
    scenarios = {
        name: _scenario(name, factor, inputs, model, scheduled)
        for name, factor in factors.items()
    }

    confidence = _confidence(inputs, model, scheduled, factors)

    return Forecast(
        as_of=inputs.as_of,
        opening_balance=inputs.opening_balance,
        safety_buffer=inputs.safety_buffer,
        horizon_days=inputs.horizon_days,
        revenue_model=model,
        recurring=recurring,
        scenarios=scenarios,
        confidence=confidence,
    )


def simulate(inputs: ForecastInputs, changes: Sequence[CashChange]) -> SimulationResult:
    """Compare the forecast without and with the given changes."""
    baseline = build_forecast(inputs)
    simulated = build_forecast(inputs, changes)

    before = baseline.scenarios[SCENARIO_BASE].indicators.lowest_balance
    after = simulated.scenarios[SCENARIO_BASE].indicators.lowest_balance

    return SimulationResult(baseline=baseline, simulated=simulated, lowest_balance_change=after - before)


def detect_recurring_payments(history: Iterable[CashRecord], as_of: date) -> Tuple[RecurringPayment, ...]:
    """Find monthly and quarterly payments (same counterparty, similar amount, regular dates)."""
    recurring, _ = _detect_recurring(_history_until(history, as_of), as_of)
    return recurring


def build_revenue_model(operating: Sequence[CashRecord], as_of: date) -> RevenueModel:
    """Weekday revenue averages, variable cost ratio, monthly seasonality and volatility."""
    window_start = as_of - timedelta(days=REVENUE_LOOKBACK_DAYS - 1)
    window = [record for record in operating if window_start <= record.booking_date <= as_of]

    weekday_inflow = _weekday_inflow(window, window_start, as_of)
    variable_cost_ratio = _variable_cost_ratio(window)

    month_factors = _month_factors(operating)
    lookback_factor = _average_factor(month_factors, window_start, as_of)

    return RevenueModel(
        weekday_inflow=weekday_inflow,
        variable_cost_ratio=variable_cost_ratio,
        month_factors=month_factors,
        lookback_factor=lookback_factor,
        volatility=_weekly_volatility(window, as_of),
    )


def expected_revenue(model: RevenueModel, day: date) -> Decimal:
    base = model.weekday_inflow[day.weekday()]
    if model.lookback_factor <= ZERO:
        return base

    return base * model.month_factors.get(day.month, ONE) / model.lookback_factor


def _ensure_horizon(horizon_days: int) -> None:
    if horizon_days < 1:
        raise ValueError("horizon_days must be at least 1")


def _history_until(history: Iterable[CashRecord], as_of: date) -> List[CashRecord]:
    return [record for record in history if record.booking_date <= as_of]


def _normalize_name(name: str) -> str:
    return " ".join(name.lower().split())


def _detect_recurring(history: Sequence[CashRecord], as_of: date) -> Tuple[Tuple[RecurringPayment, ...], set]:
    by_counterparty: Dict[str, List[int]] = defaultdict(list)
    for index, record in enumerate(history):
        key = _normalize_name(record.counterparty)
        if key and record.amount != ZERO:
            by_counterparty[key].append(index)

    payments: List[RecurringPayment] = []
    used: set = set()
    for indexes in by_counterparty.values():
        for cluster in _cluster_by_amount(history, indexes):
            payment = _as_recurring([history[index] for index in cluster], as_of)
            if payment:
                payments.append(payment)
                used.update(cluster)

    payments.sort(key=lambda payment: (payment.counterparty, payment.amount))
    return tuple(payments), used


def _cluster_by_amount(history: Sequence[CashRecord], indexes: List[int]) -> List[List[int]]:
    ordered = sorted(indexes, key=lambda index: history[index].amount)
    clusters: List[List[int]] = []

    for index in ordered:
        amount = history[index].amount
        if clusters and _similar_amount(history[clusters[-1][0]].amount, amount):
            clusters[-1].append(index)
            continue

        clusters.append([index])

    return clusters


def _similar_amount(reference: Decimal, amount: Decimal) -> bool:
    if (reference > ZERO) != (amount > ZERO):
        return False

    return abs(amount - reference) <= abs(reference) * RECURRING_AMOUNT_TOLERANCE


def _as_recurring(records: List[CashRecord], as_of: date) -> Optional[RecurringPayment]:
    if len(records) < RECURRING_MIN_OCCURRENCES:
        return None

    records = sorted(records, key=lambda record: record.booking_date)
    intervals = [(later.booking_date - earlier.booking_date).days for earlier, later in zip(records, records[1:])]

    interval_months = _matching_interval(intervals)
    if interval_months is None:
        return None

    last = records[-1]
    max_gap = RECURRING_INTERVALS_MONTHS[interval_months][1] + RECURRING_STALE_GRACE_DAYS
    if (as_of - last.booking_date).days > max_gap:
        return None

    return RecurringPayment(
        counterparty=last.counterparty,
        category=Counter(record.category for record in records).most_common(1)[0][0],
        amount=Decimal(median(record.amount for record in records)).quantize(CENT),
        interval_months=interval_months,
        day_of_month=Counter(record.booking_date.day for record in records).most_common(1)[0][0],
        last_date=last.booking_date,
        occurrences=len(records),
    )


def _matching_interval(intervals: List[int]) -> Optional[int]:
    for months, (low, high) in RECURRING_INTERVALS_MONTHS.items():
        inside = sum(1 for days in intervals if low <= days <= high)
        if Decimal(inside) >= Decimal(len(intervals)) * RECURRING_INTERVAL_SHARE:
            return months

    return None


def _add_months(start: date, months: int, day: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def _recurring_dates(payment: RecurringPayment, after: date, until: date) -> List[date]:
    dates: List[date] = []
    step = 1

    while True:
        candidate = _add_months(payment.last_date, step * payment.interval_months, payment.day_of_month)
        if candidate > until:
            return dates

        if candidate > after:
            dates.append(candidate)
        step += 1


def _weekday_inflow(window: Sequence[CashRecord], start: date, end: date) -> Tuple[Decimal, ...]:
    totals = [ZERO] * WEEKDAYS
    counts = [0] * WEEKDAYS

    for offset in range((end - start).days + 1):
        counts[(start + timedelta(days=offset)).weekday()] += 1

    for record in window:
        if record.amount > ZERO:
            totals[record.booking_date.weekday()] += record.amount

    return tuple((totals[day] / counts[day]).quantize(CENT) if counts[day] else ZERO for day in range(WEEKDAYS))


def _variable_cost_ratio(window: Sequence[CashRecord]) -> Decimal:
    inflows = sum((record.amount for record in window if record.amount > ZERO), ZERO)
    outflows = sum((-record.amount for record in window if record.amount < ZERO), ZERO)
    if inflows <= ZERO:
        return ZERO

    return (outflows / inflows).quantize(FACTOR_PRECISION)


def _month_factors(operating: Sequence[CashRecord]) -> Dict[int, Decimal]:
    if not operating:
        return {}

    first = min(record.booking_date for record in operating)
    last = max(record.booking_date for record in operating)
    span_days = (last - first).days + 1
    if span_days < SEASONALITY_MIN_HISTORY_DAYS:
        return {}

    inflow_by_month: Dict[int, Decimal] = defaultdict(lambda: ZERO)
    days_by_month: Dict[int, int] = defaultdict(int)
    for offset in range(span_days):
        days_by_month[(first + timedelta(days=offset)).month] += 1
    for record in operating:
        if record.amount > ZERO:
            inflow_by_month[record.booking_date.month] += record.amount

    overall = sum(inflow_by_month.values(), ZERO) / Decimal(span_days)
    if overall <= ZERO:
        return {}

    return {
        month: (inflow_by_month[month] / Decimal(days) / overall).quantize(FACTOR_PRECISION)
        for month, days in days_by_month.items()
    }


def _average_factor(month_factors: Dict[int, Decimal], start: date, end: date) -> Decimal:
    if not month_factors:
        return ONE

    days = (end - start).days + 1
    total = sum((month_factors.get((start + timedelta(days=offset)).month, ONE) for offset in range(days)), ZERO)
    return (total / Decimal(days)).quantize(FACTOR_PRECISION)


def _weekly_volatility(window: Sequence[CashRecord], as_of: date) -> Decimal:
    weeks = REVENUE_LOOKBACK_DAYS // WEEKDAYS
    totals = [0.0] * weeks

    for record in window:
        if record.amount <= ZERO:
            continue
        week = (as_of - record.booking_date).days // WEEKDAYS
        if week < weeks:
            totals[week] += float(record.amount)

    mean = sum(totals) / weeks
    if mean <= 0:
        return ZERO

    return Decimal(str(round(pstdev(totals) / mean, 4)))


def _scenario_factors(volatility: Decimal) -> Dict[str, Decimal]:
    spread = max(volatility * SCENARIO_VOLATILITY_MULTIPLIER, SCENARIO_MIN_SPREAD)
    return {
        SCENARIO_PESSIMISTIC: _clamp_factor(ONE - spread),
        SCENARIO_BASE: ONE,
        SCENARIO_OPTIMISTIC: _clamp_factor(ONE + spread),
    }


def _clamp_factor(factor: Decimal) -> Decimal:
    return min(max(factor, SCENARIO_MIN_REVENUE_FACTOR), SCENARIO_MAX_REVENUE_FACTOR).quantize(FACTOR_PRECISION)


def _horizon_day(inputs: ForecastInputs, day: date) -> Optional[date]:
    first_day = inputs.as_of + timedelta(days=1)
    last_day = inputs.as_of + timedelta(days=inputs.horizon_days)
    if day > last_day:
        return None

    return max(day, first_day)


def _schedule_flows(
    inputs: ForecastInputs,
    recurring: Sequence[RecurringPayment],
    changes: Sequence[CashChange],
) -> Dict[date, List[Driver]]:
    scheduled: Dict[date, List[Driver]] = defaultdict(list)

    for invoice in inputs.invoices:
        day = _horizon_day(inputs, invoice.due_date)
        if day:
            label = DRIVER_INVOICE.format(number=invoice.invoice_number, counterparty=invoice.counterparty)
            scheduled[day].append(Driver(label, invoice.amount))

    last_day = inputs.as_of + timedelta(days=inputs.horizon_days)
    for payment in recurring:
        label = DRIVER_RECURRING.format(counterparty=payment.counterparty, category=payment.category)
        for day in _recurring_dates(payment, inputs.as_of, last_day):
            if not _covered_by_invoice(payment, day, inputs.invoices):
                scheduled[day].append(Driver(label, payment.amount))

    for change in changes:
        day = _horizon_day(inputs, change.on_date)
        if day:
            scheduled[day].append(Driver(change.label, change.amount))

    return scheduled


def _covered_by_invoice(payment: RecurringPayment, day: date, invoices: Sequence[OpenInvoice]) -> bool:
    counterparty = _normalize_name(payment.counterparty)
    return any(
        _normalize_name(invoice.counterparty) == counterparty
        and (invoice.amount > ZERO) == (payment.amount > ZERO)
        and abs((invoice.due_date - day).days) <= RECURRING_INVOICE_MATCH_DAYS
        for invoice in invoices
    )


def _project(
    inputs: ForecastInputs,
    model: RevenueModel,
    scheduled: Dict[date, List[Driver]],
    factor: Decimal,
) -> Tuple[ForecastDay, ...]:
    balance = inputs.opening_balance
    days: List[ForecastDay] = []

    for offset in range(1, inputs.horizon_days + 1):
        day = inputs.as_of + timedelta(days=offset)
        drivers = _operating_drivers(model, day, factor) + scheduled.get(day, [])

        inflows = sum((driver.amount for driver in drivers if driver.amount > ZERO), ZERO)
        outflows = sum((-driver.amount for driver in drivers if driver.amount < ZERO), ZERO)
        balance += inflows - outflows

        top = sorted(drivers, key=lambda driver: abs(driver.amount), reverse=True)[:DRIVERS_PER_DAY_LIMIT]
        days.append(ForecastDay(day=day, balance=balance, inflows=inflows, outflows=outflows, drivers=tuple(top)))

    return tuple(days)


def _operating_drivers(model: RevenueModel, day: date, factor: Decimal) -> List[Driver]:
    revenue = (expected_revenue(model, day) * factor).quantize(CENT)
    costs = (revenue * model.variable_cost_ratio).quantize(CENT)

    drivers: List[Driver] = []
    if revenue:
        drivers.append(Driver(DRIVER_EXPECTED_REVENUE, revenue))
    if costs:
        drivers.append(Driver(DRIVER_VARIABLE_COSTS, -costs))
    return drivers


def _scenario(
    name: str,
    factor: Decimal,
    inputs: ForecastInputs,
    model: RevenueModel,
    scheduled: Dict[date, List[Driver]],
) -> ScenarioForecast:
    days = _project(inputs, model, scheduled, factor)
    return ScenarioForecast(name=name, revenue_factor=factor, days=days, indicators=_indicators(inputs, days))


def _indicators(inputs: ForecastInputs, days: Sequence[ForecastDay]) -> Indicators:
    lowest = min(days, key=lambda forecast_day: forecast_day.balance)
    below_buffer = next((d.day for d in days if d.balance < inputs.safety_buffer), None)
    below_zero = next((d.day for d in days if d.balance < ZERO), None)

    return Indicators(
        lowest_balance=lowest.balance,
        lowest_balance_date=lowest.day,
        first_below_buffer_date=below_buffer,
        first_below_zero_date=below_zero,
        days_to_buffer_breach=(below_buffer - inputs.as_of).days if below_buffer else None,
        runway_months=_runway_months(inputs, days),
        free_cash=lowest.balance - inputs.safety_buffer,
    )


def _runway_months(inputs: ForecastInputs, days: Sequence[ForecastDay]) -> Optional[Decimal]:
    monthly_net = (days[-1].balance - inputs.opening_balance) / Decimal(len(days)) * DAYS_PER_MONTH
    if monthly_net >= ZERO:
        return None

    return (max(inputs.opening_balance, ZERO) / -monthly_net).quantize(RUNWAY_PRECISION)


def _confidence(
    inputs: ForecastInputs,
    model: RevenueModel,
    scheduled: Dict[date, List[Driver]],
    factors: Dict[str, Decimal],
) -> Decimal:
    low = factors[SCENARIO_PESSIMISTIC]
    high = factors[SCENARIO_OPTIMISTIC]
    step = (high - low) / Decimal(CONFIDENCE_GRID_STEPS - 1)

    safe = 0
    for index in range(CONFIDENCE_GRID_STEPS):
        days = _project(inputs, model, scheduled, low + step * index)
        if min(day.balance for day in days) >= inputs.safety_buffer:
            safe += 1

    return (Decimal(safe) / Decimal(CONFIDENCE_GRID_STEPS)).quantize(CENT)
