from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.const.forecast import (
    DRIVER_EXPECTED_REVENUE,
    SCENARIO_BASE,
    SCENARIO_OPTIMISTIC,
    SCENARIO_PESSIMISTIC,
)
from app.services.forecast_engine import (
    CashChange,
    CashRecord,
    ForecastInputs,
    OpenInvoice,
    build_forecast,
    build_revenue_model,
    detect_recurring_payments,
    simulate,
)
from app.services.statement_parser import parse_bank_statement_csv

AS_OF = date(2025, 12, 31)
PIZZERIA_CSV = Path(__file__).resolve().parents[2] / "memory" / "reference" / "sample-data" / "pizzeria-amalfi-bank-statement-2025-v6.csv"


def monthly(counterparty: str, amount: str, day: int, months=range(1, 13), year=2025, category="rent"):
    return [CashRecord(date(year, month, day), Decimal(amount), counterparty, category) for month in months]


def daily(amount: str, days: int, end: date = AS_OF, counterparty="POS", category="revenue_pos"):
    return [CashRecord(end - timedelta(days=offset), Decimal(amount), counterparty, category) for offset in range(days)]


def inputs(**overrides) -> ForecastInputs:
    values = dict(
        as_of=AS_OF,
        opening_balance=Decimal("10000.00"),
        safety_buffer=Decimal("5000.00"),
        horizon_days=30,
    )
    values.update(overrides)
    return ForecastInputs(**values)


def base_days(forecast):
    return forecast.scenarios[SCENARIO_BASE].days


def test_detects_monthly_payment_with_amount_and_day():
    history = monthly("Main Street Real Estate GmbH", "-3800.00", 1)

    payments = detect_recurring_payments(history, AS_OF)

    assert len(payments) == 1
    assert payments[0].amount == Decimal("-3800.00")
    assert payments[0].interval_months == 1
    assert payments[0].day_of_month == 1


def test_splits_one_counterparty_into_monthly_and_quarterly_streams():
    history = monthly("Tax Office", "-880.00", 10, category="tax")
    history += monthly("Tax Office", "-1150.00", 10, months=(3, 6, 9, 12), category="tax")

    payments = detect_recurring_payments(history, AS_OF)

    assert {(p.amount, p.interval_months) for p in payments} == {(Decimal("-880.00"), 1), (Decimal("-1150.00"), 3)}


def test_ignores_stream_that_stopped_months_ago():
    history = monthly("Old Leasing", "-500.00", 5, months=range(1, 6))

    assert detect_recurring_payments(history, AS_OF) == ()


def test_ignores_daily_revenue_as_recurring():
    assert detect_recurring_payments(daily("300.00", 120), AS_OF) == ()


def test_invoice_moves_balance_on_due_date_and_sets_indicators():
    due = AS_OF + timedelta(days=10)
    forecast = build_forecast(inputs(invoices=(OpenInvoice("INV-1", "Flour Ltd", due, Decimal("-7000.00")),)))

    days = base_days(forecast)
    indicators = forecast.scenarios[SCENARIO_BASE].indicators

    assert days[8].balance == Decimal("10000.00")
    assert days[9].balance == Decimal("3000.00")
    assert indicators.first_below_buffer_date == due
    assert indicators.days_to_buffer_breach == 10
    assert indicators.lowest_balance == Decimal("3000.00")
    assert indicators.free_cash == Decimal("-2000.00")
    assert forecast.confidence == Decimal("0.08")


def test_overdue_invoice_is_paid_on_first_forecast_day():
    overdue = OpenInvoice("INV-OLD", "Flour Ltd", AS_OF - timedelta(days=20), Decimal("-1000.00"))

    days = base_days(build_forecast(inputs(invoices=(overdue,))))

    assert days[0].balance == Decimal("9000.00")


def test_invoice_after_horizon_is_ignored():
    late = OpenInvoice("INV-LATE", "Flour Ltd", AS_OF + timedelta(days=45), Decimal("-1000.00"))

    days = base_days(build_forecast(inputs(invoices=(late,))))

    assert days[-1].balance == Decimal("10000.00")


def test_recurring_payment_is_not_counted_twice_when_invoice_exists():
    history = monthly("Main Street Real Estate GmbH", "-3800.00", 1)
    rent_invoice = OpenInvoice("RENT-01", "Main Street Real Estate GmbH", date(2026, 1, 3), Decimal("-3800.00"))

    forecast = build_forecast(inputs(history=tuple(history), invoices=(rent_invoice,)))

    assert base_days(forecast)[-1].balance == Decimal("6200.00")


def test_weekday_revenue_profile_and_variable_cost_ratio():
    saturdays = [CashRecord(AS_OF - timedelta(days=offset), Decimal("1000.00"), "POS") for offset in range(56) if (AS_OF - timedelta(days=offset)).weekday() == 5]
    costs = [CashRecord(record.booking_date, Decimal("-300.00"), "Wholesale") for record in saturdays]

    model = build_revenue_model(saturdays + costs, AS_OF)

    assert model.weekday_inflow[5] == Decimal("1000.00")
    assert model.weekday_inflow[0] == Decimal("0")
    assert model.variable_cost_ratio == Decimal("0.3000")


def test_forecast_uses_expected_revenue_driver():
    history = tuple(daily("200.00", 56))

    first_day = base_days(build_forecast(inputs(history=history)))[0]

    assert first_day.balance == Decimal("10200.00")
    assert first_day.drivers[0].label == DRIVER_EXPECTED_REVENUE


def test_pessimistic_scenario_is_never_above_optimistic():
    history = [CashRecord(AS_OF - timedelta(days=offset), Decimal(100 + (offset % 7) * 80 + (offset // 7) * 40), "POS") for offset in range(56)]

    forecast = build_forecast(inputs(history=tuple(history)))
    lowest = {name: scenario.indicators.lowest_balance for name, scenario in forecast.scenarios.items()}

    assert lowest[SCENARIO_PESSIMISTIC] <= lowest[SCENARIO_BASE] <= lowest[SCENARIO_OPTIMISTIC]
    assert forecast.scenarios[SCENARIO_PESSIMISTIC].revenue_factor < Decimal("1")


def test_simulation_shows_effect_of_credit_line():
    invoice = OpenInvoice("INV-1", "Flour Ltd", AS_OF + timedelta(days=10), Decimal("-7000.00"))
    credit_line = CashChange(AS_OF + timedelta(days=3), Decimal("5000.00"), "Credit line")

    result = simulate(inputs(invoices=(invoice,)), [credit_line])

    assert result.lowest_balance_change == Decimal("5000.00")
    assert result.baseline.confidence == Decimal("0.08")
    assert result.simulated.confidence == Decimal("0.92")
    assert result.simulated.scenarios[SCENARIO_BASE].indicators.first_below_buffer_date is None


def test_horizon_must_be_positive():
    with pytest.raises(ValueError):
        build_forecast(inputs(horizon_days=0))


@pytest.mark.skipif(not PIZZERIA_CSV.exists(), reason="sample data not available")
def test_pizzeria_sample_data_recurring_payments_and_forecast():
    parsed = parse_bank_statement_csv(PIZZERIA_CSV.read_text(encoding="utf-8"))
    history = tuple(
        CashRecord(tx["booking_date"], tx["amount_base_currency"], tx["counterparty_name"], tx["category"])
        for tx in parsed
    )

    forecast = build_forecast(inputs(history=history, opening_balance=Decimal("33266.35"), horizon_days=90))
    payments = {(p.counterparty, p.amount, p.interval_months) for p in forecast.recurring}

    assert ("Main Street Real Estate GmbH", Decimal("-3800.00"), 1) in payments
    assert ("Tax Office Frankfurt am Main", Decimal("-880.00"), 1) in payments
    assert ("Tax Office Frankfurt am Main", Decimal("-1150.00"), 3) in payments
    assert len(base_days(forecast)) == 90
    assert forecast.revenue_model.month_factors


def test_invoice_with_different_amount_keeps_recurring_payment():
    history = monthly("Tax Office", "-880.00", 10, category="tax")
    yearly_tax = OpenInvoice("EST-2024", "Tax Office", date(2026, 1, 15), Decimal("-21000.00"))

    days = base_days(build_forecast(inputs(history=tuple(history), invoices=(yearly_tax,))))

    assert days[-1].balance == Decimal("10000.00") - Decimal("880.00") - Decimal("21000.00")


def test_simulation_starts_from_planned_decisions():
    planned = [CashChange(AS_OF + timedelta(days=2), Decimal("-3000.00"), "Approved card")]
    change = CashChange(AS_OF + timedelta(days=4), Decimal("1000.00"), "New idea")

    result = simulate(inputs(), [change], planned)

    assert base_days(result.baseline)[-1].balance == Decimal("7000.00")
    assert base_days(result.simulated)[-1].balance == Decimal("8000.00")
