from datetime import datetime, timedelta

import pytest

from app.services.statement_parser import parse_bank_statement_csv
from scripts.generate_test_data import PROFILES, backtest, generate_statement


@pytest.mark.parametrize("profile", sorted(PROFILES))
def test_generated_statement_goes_through_the_real_parser(profile):
    text = generate_statement(profile, years=2, seed=1)

    transactions = parse_bank_statement_csv(text)
    days = {tx["booking_date"] for tx in transactions}

    assert len(transactions) > 200
    assert max(days) - min(days) >= timedelta(days=700)
    assert {tx["currency"] for tx in transactions} == {PROFILES[profile].currency}


def test_generator_is_deterministic_per_seed():
    assert generate_statement("pizzeria", seed=3) == generate_statement("pizzeria", seed=3)
    assert generate_statement("pizzeria", seed=3) != generate_statement("pizzeria", seed=4)


def test_pizzeria_has_price_drift_closure_and_late_free_revenue():
    transactions = parse_bank_statement_csv(generate_statement("pizzeria", seed=1))
    produce = sorted((tx for tx in transactions if tx["counterparty_name"] == "Central Wholesale Market"), key=lambda tx: tx["booking_date"])
    first_year = [-tx["amount"] for tx in produce[:100]]
    last_year = [-tx["amount"] for tx in produce[-100:]]

    assert sum(last_year) / len(last_year) > sum(first_year) / len(first_year)
    assert not [tx for tx in transactions if tx["category"] == "revenue_pos" and tx["booking_date"].month == 6 and 2 <= tx["booking_date"].day <= 22]


def test_software_house_clients_pay_late():
    transactions = parse_bank_statement_csv(generate_statement("software_house", seed=1))
    delays = []
    for tx in transactions:
        if tx["counterparty_name"] == "Startup Labs Sp. z o.o.":
            issued = datetime.strptime(tx["payment_reference"].split("-")[-1], "%Y%m").date()
            delays.append((tx["booking_date"] - issued - timedelta(days=30)).days)

    assert delays and min(delays) >= 30


@pytest.mark.parametrize("profile", ["pizzeria", "beauty_salon"])
def test_backtest_runs_on_the_second_year(profile):
    result = backtest(profile, generate_statement(profile, seed=1))

    assert result.horizon_days == 60
    assert result.average_daily_revenue > 0
    assert result.relative_error < 10
