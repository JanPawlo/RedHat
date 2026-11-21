from tests.conftest import API_PREFIX

BANKS = f"{API_PREFIX}/bank-connections"
BANK_ID = "ing-business"


def _bank(client, auth_headers, bank_id=BANK_ID):
    banks = client.get(BANKS, headers=auth_headers).json()
    return next(bank for bank in banks if bank["id"] == bank_id)


def test_connect_sync_disconnect(client, auth_headers):
    client.delete(f"{BANKS}/{BANK_ID}", headers=auth_headers)
    assert _bank(client, auth_headers)["status"] == "available"

    connected = client.post(f"{BANKS}/{BANK_ID}", headers=auth_headers)
    assert connected.status_code == 201, connected.text
    body = connected.json()
    assert body["status"] == "connected"
    assert body["consent_valid_until"]
    assert body["accounts"][0]["transactions"] > 0

    synced = client.post(f"{BANKS}/{BANK_ID}/sync", headers=auth_headers)
    assert synced.status_code == 200
    assert synced.json()["imported"] == 0
    assert synced.json()["skipped"] > 0

    account_id = body["accounts"][0]["id"]
    accounts = client.get(f"{API_PREFIX}/accounts", headers=auth_headers).json()
    assert any(account["id"] == account_id and not account["is_primary"] for account in accounts)

    assert client.delete(f"{BANKS}/{BANK_ID}", headers=auth_headers).status_code == 204
    assert _bank(client, auth_headers)["status"] == "available"


def test_connect_twice_returns_409(client, auth_headers):
    bank_id = "wise-business"
    client.delete(f"{BANKS}/{bank_id}", headers=auth_headers)
    assert client.post(f"{BANKS}/{bank_id}", headers=auth_headers).status_code == 201

    assert client.post(f"{BANKS}/{bank_id}", headers=auth_headers).status_code == 409

    client.delete(f"{BANKS}/{bank_id}", headers=auth_headers)


def test_unknown_bank_returns_404(client, auth_headers):
    assert client.post(f"{BANKS}/no-such-bank", headers=auth_headers).status_code == 404


def test_sync_not_connected_returns_409(client, auth_headers):
    client.delete(f"{BANKS}/deutsche-bank", headers=auth_headers)

    assert client.post(f"{BANKS}/deutsche-bank/sync", headers=auth_headers).status_code == 409


def test_bank_connections_need_login(client):
    assert client.get(BANKS).status_code == 401
