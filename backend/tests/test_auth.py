from tests.conftest import API_PREFIX, TEST_PASSWORD, register, unique_email


def test_endpoint_without_token_returns_401(client):
    response = client.get(f"{API_PREFIX}/accounts")

    assert response.status_code == 401


def test_register_then_login(client):
    email = unique_email()
    assert register(client, email).status_code == 201

    response = client.post(f"{API_PREFIX}/auth/login", json={"email": email, "password": TEST_PASSWORD})

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_register_same_email_twice_returns_409(client):
    email = unique_email()
    assert register(client, email).status_code == 201

    assert register(client, email).status_code == 409


def test_login_with_wrong_password_returns_401(client):
    email = unique_email()
    register(client, email)

    response = client.post(f"{API_PREFIX}/auth/login", json={"email": email, "password": "wrong-password"})

    assert response.status_code == 401
