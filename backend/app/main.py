import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.const.app import (
    API_HEALTH_PATH,
    AUTH_DISABLED_WARNING,
    HEALTH_PATH,
    HEALTH_STATUS_OK,
    LOG_FORMAT,
    STARTUP_LOGGER_NAME,
)
from app.const.auth import ADMIN_CREATED_MESSAGE
from app.const.docs import API_TITLE_DESCRIPTION, OPENAPI_TAGS, SWAGGER_UI_PARAMETERS, TAG_HEALTH
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.migrations import run_migrations
from app.core.openapi import grouped_openapi
from app.managers.auth_manager import ensure_admin_account
from app.managers.card_manager import reset_decisions
from app.api.v1.router import api_router
from app.services.seed import seed_data

logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO, format=LOG_FORMAT)

logger = logging.getLogger(STARTUP_LOGGER_NAME)


async def _reset_decisions() -> None:
    async with AsyncSessionLocal() as db:
        count = await reset_decisions(db)
        await db.commit()

    logger.info("Demo reset: %d decided cards set back to pending", count)


async def _ensure_admin_account() -> None:
    async with AsyncSessionLocal() as db:
        admin = await ensure_admin_account(db, settings.ADMIN_LOGIN, settings.ADMIN_PASSWORD)
        await db.commit()

    if admin:
        logger.info(ADMIN_CREATED_MESSAGE.format(login=admin.email))


async def _seed_demo_data() -> None:
    if not settings.SEED_DEMO_DATA:
        return

    await seed_data()


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    await _ensure_admin_account()
    await _seed_demo_data()

    if settings.RESET_DECISIONS_ON_START:
        await _reset_decisions()

    if settings.AUTH_DISABLED:
        logger.warning(AUTH_DISABLED_WARNING)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=API_TITLE_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
    swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.openapi = grouped_openapi(app)


@app.get(API_HEALTH_PATH, tags=[TAG_HEALTH], summary="Health check")
@app.get(HEALTH_PATH, include_in_schema=False)
async def health_check():
    return {"status": HEALTH_STATUS_OK, "app": settings.APP_NAME}


@app.get("/", tags=[TAG_HEALTH], summary="API info and link to the docs")
async def root():
    return {
        "message": "Autonomous CFO API is running. Check /docs for Swagger UI.",
        "version": "0.1.0",
    }
