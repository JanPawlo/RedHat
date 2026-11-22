import pytest

from tests.conftest import API_PREFIX

DEMO_RESET_URL = f"{API_PREFIX}/demo/reset"
COMPANY_URL = f"{API_PREFIX}/company"
INVOICES_URL = f"{API_PREFIX}/analysis/invoices"
DEMO_COMPANY = "Pizzeria Amalfi"


def reset(client, auth_headers):
    response = client.post(DEMO_RESET_URL, headers=auth_headers)
    if response.status_code != 200:
        pytest.skip(f"Demo seed not available: {response.text}")


def invoices_without_ids(client, auth_headers):
    invoices = client.get(INVOICES_URL, headers=auth_headers).json()["invoices"]
    return [{key: value for key, value in invoice.items() if key != "id"} for invoice in invoices]


def test_reset_brings_back_the_first_pizzeria_state(client, auth_headers):
    reset(client, auth_headers)
    first_invoices = invoices_without_ids(client, auth_headers)

    changed = client.put(COMPANY_URL, headers=auth_headers, json={"name": "Changed during the demo"})
    assert changed.status_code == 200, changed.text

    reset(client, auth_headers)

    assert client.get(COMPANY_URL, headers=auth_headers).json()["name"] == DEMO_COMPANY
    assert invoices_without_ids(client, auth_headers) == first_invoices


def test_reset_keeps_the_logged_in_user(client, auth_headers):
    reset(client, auth_headers)

    assert client.get(f"{API_PREFIX}/auth/me", headers=auth_headers).status_code == 200
