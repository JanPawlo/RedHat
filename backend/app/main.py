import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.const.app import API_HEALTH_PATH, HEALTH_PATH, HEALTH_STATUS_OK, LOG_FORMAT, STARTUP_LOGGER_NAME
from app.const.auth import ADMIN_CREATED_MESSAGE
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.migrations import run_migrations
from app.managers.auth_manager import ensure_admin_account
from app.api.v1.router import api_router

logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO, format=LOG_FORMAT)

logger = logging.getLogger(STARTUP_LOGGER_NAME)


async def _ensure_admin_account() -> None:
    async with AsyncSessionLocal() as db:
        admin = await ensure_admin_account(db, settings.ADMIN_LOGIN, settings.ADMIN_PASSWORD)
        await db.commit()

    if admin:
        logger.info(ADMIN_CREATED_MESSAGE.format(login=admin.email))


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    await _ensure_admin_account()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Agentic Autonomous CFO API for SMEs - Red Hat Collabothon 2026",
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


@app.get(API_HEALTH_PATH, tags=["Health"])
@app.get(HEALTH_PATH, include_in_schema=False)
async def health_check():
    return {"status": HEALTH_STATUS_OK, "app": settings.APP_NAME}


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Autonomous CFO API is running. Check /docs for Swagger UI.",
        "version": "0.1.0",
    }
