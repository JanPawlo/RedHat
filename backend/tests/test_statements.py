import uuid

from tests.conftest import API_PREFIX

UPLOAD_URL = f"{API_PREFIX}/statements/upload/csv"
HEADER = '"Account Number";"Booking Date";"Value Date";"Transaction Type";"Payment Reference";' \
         '"Beneficiary/Payer";"Counterparty Account";"Bank Code";"Amount";"Currency";"Info"'


def _row(account_number: str, amount: str = "-5,00", currency: str = "EUR") -> str:
    return f'"{account_number}";"01.03.25";"01.03.25";"Card Payment";"";"Bakery";"";"";"{amount}";"{currency}";""'


def _upload(client, auth_headers, rows):
    content = "\n".join([HEADER, *rows]).encode("utf-8")
    return client.post(UPLOAD_URL, headers=auth_headers, files={"file": ("statement.csv", content, "text/csv")})


def _new_account_number() -> str:
    return f"DE{uuid.uuid4().int % 10**20:020d}"


def test_identical_rows_are_all_imported_and_reimport_skips_them(client, auth_headers):
    account_number = _new_account_number()
    rows = [_row(account_number)] * 3

    first = _upload(client, auth_headers, rows)
    assert first.status_code == 200, first.text
    assert first.json()["transactions_imported"] == 3

    second = _upload(client, auth_headers, rows)
    assert second.json()["transactions_imported"] == 0
    assert second.json()["duplicates_skipped"] == 3

    third = _upload(client, auth_headers, rows + [_row(account_number)])
    assert third.json()["transactions_imported"] == 1


def test_nan_amount_returns_400(client, auth_headers):
    response = _upload(client, auth_headers, [_row(_new_account_number(), amount="NaN")])

    assert response.status_code == 400


def test_amount_out_of_range_returns_400(client, auth_headers):
    response = _upload(client, auth_headers, [_row(_new_account_number(), amount="1e20")])

    assert response.status_code == 400


def test_too_long_account_number_returns_400(client, auth_headers):
    response = _upload(client, auth_headers, [_row("X" * 100)])

    assert response.status_code == 400


def test_bad_currency_returns_400(client, auth_headers):
    response = _upload(client, auth_headers, [_row(_new_account_number(), currency="EURO")])

    assert response.status_code == 400


def test_non_csv_file_returns_400(client, auth_headers):
    response = client.post(UPLOAD_URL, headers=auth_headers, files={"file": ("statement.txt", b"x", "text/plain")})

    assert response.status_code == 400
