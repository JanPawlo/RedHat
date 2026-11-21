from typing import List, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.const.app import (
    AUTH_DISABLED_OUTSIDE_DEVELOPMENT_MESSAGE,
    DEFAULT_CORS_ORIGINS,
    DEVELOPMENT_ENV,
    INSECURE_JWT_SECRET_MESSAGE,
)
from app.const.auth import DEFAULT_ADMIN_LOGIN, DEV_JWT_SECRET_KEY


class Settings(BaseSettings):
    APP_NAME: str = "Autonomous CFO API"
    APP_ENV: str = DEVELOPMENT_ENV
    DEBUG: bool = False
    SQL_ECHO: bool = False
    PORT: int = 8000
    CORS_ORIGINS: List[str] = DEFAULT_CORS_ORIGINS

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://cfo_user:cfo_password@localhost:5432/cfo_db"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://cfo_user:cfo_password@localhost:5432/cfo_db"

    # AI Model Endpoint on OpenShift AI (RHOAI vLLM / MaaS)
    MODEL_ENDPOINT_URL: str = "http://localhost:8080/v1"
    MODEL_NAME: Optional[str] = "qwen3-8b"
    MODEL_API_KEY: Optional[str] = None

    # Auth (JWT)
    JWT_SECRET_KEY: str = DEV_JWT_SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALLOW_REGISTRATION: Optional[bool] = None
    AUTH_DISABLED: bool = False
    RESET_DECISIONS_ON_START: bool = False

    # Admin account
    ADMIN_LOGIN: str = DEFAULT_ADMIN_LOGIN
    ADMIN_PASSWORD: Optional[str] = None

    # Demo data
    SEED_CSV_PATH: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore"
    )

    @model_validator(mode="after")
    def _require_real_jwt_secret(self) -> "Settings":
        if self.APP_ENV != DEVELOPMENT_ENV and self.JWT_SECRET_KEY == DEV_JWT_SECRET_KEY:
            raise ValueError(INSECURE_JWT_SECRET_MESSAGE)
        return self

    @model_validator(mode="after")
    def _auth_disabled_only_in_development(self) -> "Settings":
        if self.AUTH_DISABLED and self.APP_ENV != DEVELOPMENT_ENV:
            raise ValueError(AUTH_DISABLED_OUTSIDE_DEVELOPMENT_MESSAGE)
        return self

    @property
    def registration_enabled(self) -> bool:
        if self.ALLOW_REGISTRATION is not None:
            return self.ALLOW_REGISTRATION

        return self.APP_ENV == DEVELOPMENT_ENV


settings = Settings()
