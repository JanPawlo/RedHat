from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Autonomous CFO API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://cfo_user:cfo_password@localhost:5432/cfo_db"
    SYNC_DATABASE_URL: str = "postgresql://cfo_user:cfo_password@localhost:5432/cfo_db"

    # AI Model Endpoint on OpenShift AI (RHOAI vLLM / MaaS)
    MODEL_ENDPOINT_URL: Optional[str] = "http://localhost:8080/v1"
    MODEL_NAME: Optional[str] = "granite-3.0-8b-instruct"
    MODEL_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
