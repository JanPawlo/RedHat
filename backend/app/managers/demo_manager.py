import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.seed import seed_data

KEPT_TABLES = ("users", "alembic_version")

_reset_lock = asyncio.Lock()


async def reset_demo(db: AsyncSession) -> None:
    """
    Bring the database back to the first Pizzeria Amalfi state: every table except user accounts is emptied,
    then the demo company is seeded again. A reset requested while another one runs waits for it and returns,
    because two parallel seeds insert the same bank account twice.
    """
    if _reset_lock.locked():
        async with _reset_lock:
            return

    async with _reset_lock:
        await _truncate_demo_data(db)
        await seed_data()


async def _truncate_demo_data(db: AsyncSession) -> None:
    result = await db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
    tables = [name for name in result.scalars() if name not in KEPT_TABLES]

    quoted = ", ".join(f'"{name}"' for name in tables)
    await db.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))
    await db.commit()
