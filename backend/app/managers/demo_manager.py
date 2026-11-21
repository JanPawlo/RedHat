from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.seed import seed_data

DEMO_DATA_TABLES = "agent_actions, liquidity_forecasts, invoices, transactions, bank_accounts, company_profile"


async def reset_demo(db: AsyncSession) -> None:
    """Delete all company data and decisions (user accounts stay), then seed the demo company again."""
    await db.execute(text(f"TRUNCATE {DEMO_DATA_TABLES} CASCADE"))
    await db.commit()

    await seed_data()
