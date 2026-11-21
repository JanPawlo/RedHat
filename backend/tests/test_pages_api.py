import pytest

from tests.conftest import API_PREFIX

PAGES_URL = f"{API_PREFIX}/analysis"
DEMO_RESET_URL = f"{API_PREFIX}/demo/reset"


@pytest.fixture(scope="module")
def demo_data(client, auth_headers):
    response = client.post(DEMO_RESET_URL, headers=auth_headers)
    if response.status_code != 200:
        pytest.skip(f"Demo seed not available: {response.text}")

def test_pages_require_login(client):
    for page in ("invoices", "calendar", "risk", "advisor-facts"):
        assert client.get(f"{PAGES_URL}/{page}").status_code == 401

def test_invoices_page_shape(client, auth_headers, demo_data):
    response = client.get(f"{PAGES_URL}/invoices", headers=auth_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert [group["id"] for group in body["groups"]] == ["overdue", "today", "week", "later"]
    assert isinstance(body["invoices"], list)
    assert {"count", "amount", "note"} <= set(body["paidThisMonth"])
    discounted = [invoice for invoice in body["invoices"] if invoice["discount"]]
    assert [invoice["number"] for invoice in discounted] == ["AS-80115"]
    assert discounted[0]["discountSaving"] == 128.4

def test_cash_calendar_has_five_weeks_from_monday(client, auth_headers, demo_data):
    response = client.get(f"{PAGES_URL}/calendar", headers=auth_headers)

    assert response.status_code == 200, response.text
    days = response.json()["days"]
    assert len(days) == 35
    assert sum(1 for day in days if day["today"]) == 1
    assert all(0 <= day["level"] <= 5 for day in days)
    assert any(day["level"] == 1 for day in days), "the January gap under the buffer should be the tightest level"

def test_risk_page_scores_from_rules(client, auth_headers, demo_data):
    response = client.get(f"{PAGES_URL}/risk", headers=auth_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert 0 <= body["score"] <= 100
    assert [factor["label"] for factor in body["factors"]][0] == "Liquidity"
    assert body["counts"]["all"] == len(body["counterparties"])
    assert body["counts"]["watchlist"] == len(body["watchlist"])
    late_client = next(company for company in body["counterparties"] if company["name"] == "Frankfurter Hof Catering")
    assert late_client["watch"] and late_client["payments"][0] == "Pays 17 days late"

def test_advisor_facts_come_from_the_engine(client, auth_headers, demo_data):
    response = client.get(f"{PAGES_URL}/advisor-facts", headers=auth_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert {"bank_balance", "safety_buffer", "lowest_balance_next_days", "upcoming_payments"} <= set(body)

def test_analysis_counts_foreign_transfers_in_the_account_currency(client, auth_headers, demo_data):
    response = client.get(PAGES_URL, headers=auth_headers)

    assert response.status_code == 200, response.text
    codes = {issue["code"] for issue in response.json()["dataQuality"]["issues"]}
    assert "currency_mismatch" not in codes
