import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.llm_cache import explain_cache
from app.services.llm_limiter import reset_limiter

API_PREFIX = "/api/v1"
TEST_PASSWORD = "release-test-password"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


def unique_email() -> str:
    return f"user-{uuid.uuid4().hex}@example.com"


def register(client: TestClient, email: str):
    return client.post(f"{API_PREFIX}/auth/register", json={"email": email, "password": TEST_PASSWORD})


@pytest.fixture(scope="session")
def auth_headers(client):
    response = register(client, unique_email())
    assert response.status_code == 201, response.text

    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(autouse=True)
def fresh_llm_limits():
    reset_limiter()
    explain_cache.clear()
    yield
