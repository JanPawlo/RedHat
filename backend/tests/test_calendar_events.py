from datetime import date, timedelta
from decimal import Decimal

from app.const.calendar import EFFECT_SOURCE_ESTIMATE, EFFECT_SOURCE_MEASURED, EVENT_DRIVER_PREFIX, EVENT_KIND_COMPANY
from app.const.forecast import DRIVER_EXPECTED_REVENUE, SCENARIO_BASE
from app.services.calendar_events import (
    EventOccurrence,
    calendar_occurrences,
    company_event_definitions,
    easter_sunday,
    event_facts,
    measure_effects,
)
from app.services.forecast_engine import CashRecord, ForecastInputs, build_forecast
from tests.conftest import API_PREFIX
from tests.test_pages_api import demo_data  # noqa: F401

HISTORY_START = date(2024, 12, 1)
AS_OF = date(2025, 11, 30)


def closure(year: int, effect: str = "-0.30") -> EventOccurrence:
    return EventOccurrence("closure", "Christmas closure", EVENT_KIND_COMPANY, date(year, 12, 24), date(year, 12, 26), Decimal(effect))


def daily_history(start: date, end: date, amount: str = "100.00", zero_days=()) -> tuple:
    days = (end - start).days + 1
    records = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        value = Decimal("0") if day in zero_days else Decimal(amount)
        if value:
            records.append(CashRecord(day, value, f"Customer {offset}", "revenue_pos"))
    return tuple(records)


def revenue_by_day(forecast):
    totals = {}
    for day in forecast.scenarios[SCENARIO_BASE].days:
        totals[day.day] = sum(
            (driver.amount for driver in day.drivers if driver.label == DRIVER_EXPECTED_REVENUE or driver.label.startswith(EVENT_DRIVER_PREFIX)),
            Decimal("0"),
        )
    return totals


def test_easter_dates():
    assert easter_sunday(2025) == date(2025, 4, 20)
    assert easter_sunday(2026) == date(2026, 4, 5)


def test_polish_calendar_has_movable_holidays_and_wraps_years():
    occurrences = calendar_occurrences("PL", 2025, 2025)
    by_key = {occurrence.key: occurrence for occurrence in occurrences}

    assert by_key["pl_corpus_christi"].start == date(2025, 6, 19)
    assert by_key["pl_christmas"].start == date(2025, 12, 24)
    assert calendar_occurrences(None, 2025, 2025) == occurrences


def test_company_events_from_settings_skip_invalid_entries():
    definitions = company_event_definitions([
        {"name": "Summer closure", "start": "06-01", "end": "06-30", "assumed_effect": "-1"},
        {"name": "Broken", "start": "6/1", "end": "06-30"},
        {"start": "06-01", "end": "06-30"},
        "not a dict",
    ])

    assert len(definitions) == 1
    assert definitions[0][1] == "Summer closure" and definitions[0][5] == Decimal("-1")


def test_effect_is_measured_against_the_weeks_around_the_event():
    zero_days = {date(2024, 12, 24), date(2024, 12, 25), date(2024, 12, 26)}
    inflows = {record.booking_date: record.amount for record in daily_history(HISTORY_START, AS_OF, zero_days=zero_days)}

    measured = measure_effects((closure(2024), closure(2025)), inflows, HISTORY_START, AS_OF)

    assert measured["closure"].effect == Decimal("-1")
    assert measured["closure"].occurrences == 1
    assert measured["closure"].months == (12,)


def test_measured_event_is_not_counted_twice_when_month_seasonality_has_it():
    zero_days = {date(2024, 12, 24), date(2024, 12, 25), date(2024, 12, 26)}
    history = daily_history(HISTORY_START, AS_OF, zero_days=zero_days)
    common = dict(as_of=AS_OF, opening_balance=Decimal("10000"), safety_buffer=Decimal("1000"), horizon_days=31, history=history)

    without = build_forecast(ForecastInputs(**common))
    with_events = build_forecast(ForecastInputs(**common, events=(closure(2024), closure(2025))))

    event = with_events.events[0]
    assert event.source == EFFECT_SOURCE_MEASURED and event.already_in_base
    assert event.event_days_change < Decimal("-250")
    assert abs(event.revenue_change) < Decimal("1.00")

    before, after = revenue_by_day(without), revenue_by_day(with_events)
    assert abs(sum(after.values()) - sum(before.values())) < Decimal("1.00"), "month total must stay the same"
    assert after[date(2025, 12, 25)] == Decimal("0")
    assert abs(after[date(2025, 12, 10)] - Decimal("100")) < Decimal("0.10")
    assert before[date(2025, 12, 10)] < Decimal("95")


def test_estimate_is_applied_in_full_when_history_does_not_cover_the_event():
    as_of = date(2025, 12, 15)
    history = daily_history(date(2025, 10, 1), as_of)
    inputs = ForecastInputs(as_of=as_of, opening_balance=Decimal("10000"), safety_buffer=Decimal("1000"), horizon_days=20, history=history, events=(closure(2025),))

    forecast = build_forecast(inputs)

    event = forecast.events[0]
    assert event.source == EFFECT_SOURCE_ESTIMATE and not event.already_in_base
    assert revenue_by_day(forecast)[date(2025, 12, 24)] == Decimal("70.00")
    assert event.revenue_change == Decimal("-90.00")
    assert event_facts(forecast.events)[0]["revenue_effect_percent"] == -30


def test_forecast_api_lists_calendar_events(client, auth_headers, demo_data):  # noqa: F811
    forecast = client.get(f"{API_PREFIX}/forecast", headers=auth_headers).json()
    facts = client.get(f"{API_PREFIX}/analysis/advisor-facts", headers=auth_headers).json()

    assert isinstance(forecast["events"], list)
    assert {event["source"] for event in forecast["events"]} <= {EFFECT_SOURCE_MEASURED, EFFECT_SOURCE_ESTIMATE}
    assert "calendar_events" in facts and "calendar_events_meaning" in facts


def _effect(change: str, start: date = date(2026, 6, 1)):
    from app.services.calendar_events import EventEffect

    return EventEffect("closure", "Summer closure", EVENT_KIND_COMPANY, start, start + timedelta(days=29), Decimal("-1"),
                       EFFECT_SOURCE_MEASURED, 1, True, Decimal("0"), Decimal(change))


def test_liquidity_card_names_an_event_only_when_it_explains_the_gap():
    from app.managers.card_manager import _gap_event, _seasonal_prefix

    lowest_day = date(2026, 7, 3)

    assert _gap_event([_effect("-30000")], lowest_day, Decimal("22000")).name == "Summer closure"
    assert _gap_event([_effect("-500")], lowest_day, Decimal("22000")) is None
    assert _gap_event([_effect("-30000", start=date(2026, 8, 1))], lowest_day, Decimal("22000")) is None
    assert _seasonal_prefix(_effect("-30000")).startswith("Seasonal liquidity · Summer closure")
