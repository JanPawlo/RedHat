import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_auth_disabled_is_refused_outside_development():
    with pytest.raises(ValidationError):
        Settings(APP_ENV="production", JWT_SECRET_KEY="a-real-secret", AUTH_DISABLED=True)


def test_auth_disabled_is_allowed_in_development():
    assert Settings(APP_ENV="development", AUTH_DISABLED=True).AUTH_DISABLED is True
