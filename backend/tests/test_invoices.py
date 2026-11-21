import uuid

from tests.conftest import API_PREFIX


def test_invoice_with_unknown_account_returns_404(client, auth_headers):
    payload = {
        "invoice_number": f"INV-{uuid.uuid4().hex[:8]}",
        "issue_date": "2025-03-01",
        "due_date": "2025-03-15",
        "counterparty_name": "Test Supplier",
        "net_amount": "100.00",
        "tax_amount": "19.00",
        "gross_amount": "119.00",
        "account_id": str(uuid.uuid4()),
    }

    response = client.post(f"{API_PREFIX}/invoices", headers=auth_headers, json=payload)

    assert response.status_code == 404
