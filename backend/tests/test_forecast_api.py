import uuid
from datetime import date, timedelta

from tests.conftest import API_PREFIX

FORECAST_URL = f"{API_PREFIX}/forecast"
UPLOAD_URL = f"{API_PREFIX}/statements/upload/csv"
HEADER = '"Account Number";"Booking Date";"Value Date";"Transaction Type";"Payment Reference";' \
         '"Beneficiary/Payer";"Counterparty Account";"Bank Code";"Amount";"Currency";"Info"'
LAST_DAY = date(2025, 4, 30)


def _row(account_number: str, day: date, counterparty: str, amount: str) -> str:
    booked = day.strftime("%d.%m.%y")
    return f'"{account_number}";"{booked}";"{booked}";"Transfer";"";"{counterparty}";"";"";"{amount}";"EUR";""'


def _import_account(client, auth_headers) -> str:
    account_number = f"DE{uuid.uuid4().int % 10**20:020d}"
    rows = [_row(account_number, date(2025, month, 1), "Landlord GmbH", "-1000,00") for month in range(1, 5)]
    rows += [_row(account_number, LAST_DAY - timedelta(days=offset), "Card Customers", "200,00") for offset in range(56)]

    content = "\n".join([HEADER, *rows]).encode("utf-8")
    response = client.post(UPLOAD_URL, headers=auth_headers, files={"file": ("statement.csv", content, "text/csv")})
    assert response.status_code == 200, response.text

    accounts = client.get(f"{API_PREFIX}/accounts", headers=auth_headers).json()
    return next(account["id"] for account in accounts if account["account_number"] == account_number)


def test_forecast_requires_login(client):
    assert client.get(FORECAST_URL).status_code == 401


def test_forecast_for_imported_account(client, auth_headers):
    account_id = _import_account(client, auth_headers)

    response = client.get(FORECAST_URL, headers=auth_headers, params={"account_id": account_id, "horizon_days": 30})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["as_of"] == LAST_DAY.isoformat()
    assert set(body["scenarios"]) == {"pessimistic", "base", "optimistic"}
    assert len(body["scenarios"]["base"]["days"]) == 30
    assert [payment["counterparty"] for payment in body["recurring"]] == ["Landlord GmbH"]


def test_simulation_returns_difference(client, auth_headers):
    account_id = _import_account(client, auth_headers)
    change = {"on_date": (LAST_DAY + timedelta(days=1)).isoformat(), "amount": "2500.00", "label": "Credit line"}

    response = client.post(
        f"{FORECAST_URL}/simulate",
        headers=auth_headers,
        params={"account_id": account_id, "horizon_days": 30},
        json={"changes": [change]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["lowest_balance_change"] == "2500.00"


def test_unknown_account_returns_404(client, auth_headers):
    response = client.get(FORECAST_URL, headers=auth_headers, params={"account_id": str(uuid.uuid4())})

    assert response.status_code == 404


def test_horizon_out_of_range_returns_422(client, auth_headers):
    response = client.get(FORECAST_URL, headers=auth_headers, params={"horizon_days": 365})

    assert response.status_code == 422


def test_simulation_without_changes_returns_422(client, auth_headers):
    response = client.post(f"{FORECAST_URL}/simulate", headers=auth_headers, json={"changes": []})

    assert response.status_code == 422
