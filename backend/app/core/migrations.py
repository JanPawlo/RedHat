import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, pool, text

from app.const.app import STARTUP_LOGGER_NAME
from app.const.migrations import (
    MIGRATIONS_FINISHED_MESSAGE,
    MIGRATIONS_FOLDER_NAME,
    MIGRATIONS_LOCK_KEY,
    MIGRATIONS_LOCK_SQL,
    MIGRATIONS_STARTED_MESSAGE,
    MIGRATIONS_TARGET_REVISION,
)
from app.core.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[2]

logger = logging.getLogger(STARTUP_LOGGER_NAME)


def _build_alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / MIGRATIONS_FOLDER_NAME))
    return config


def run_migrations() -> None:
    lock_engine = create_engine(settings.SYNC_DATABASE_URL, poolclass=pool.NullPool)

    with lock_engine.connect() as lock_connection:
        lock_connection.execute(text(MIGRATIONS_LOCK_SQL), {"key": MIGRATIONS_LOCK_KEY})
        logger.info(MIGRATIONS_STARTED_MESSAGE)

        command.upgrade(_build_alembic_config(), MIGRATIONS_TARGET_REVISION)

        logger.info(MIGRATIONS_FINISHED_MESSAGE)
