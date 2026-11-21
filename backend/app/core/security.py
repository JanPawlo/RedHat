import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from app.const.auth import (
    JWT_REQUIRED_CLAIMS,
    PASSWORD_HASH_ALGORITHM,
    PASSWORD_HASH_ITERATIONS,
    PASSWORD_SALT_BYTES,
)
from app.core.config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS)

    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"{PASSWORD_HASH_ALGORITHM}${PASSWORD_HASH_ITERATIONS}${salt_b64}${digest_b64}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = password_hash.split("$")
    except ValueError:
        return False

    if algorithm != PASSWORD_HASH_ALGORITHM:
        return False

    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(digest_b64)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(actual, expected)


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {"sub": subject, "iat": now, "exp": expires_at}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": JWT_REQUIRED_CLAIMS},
        )
    except jwt.PyJWTError:
        return None

    return payload.get("sub")
