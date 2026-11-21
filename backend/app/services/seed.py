import asyncio
import logging
import os
import sys
from decimal import Decimal
from sqlalchemy import select

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.const.app import LOG_FORMAT
from app.const.company import DEFAULT_CURRENCY_RISK_THRESHOLD, DEFAULT_MIN_SAFETY_BUFFER, MIN_SAFETY_BUFFER_KEY
from app.const.messages import SEED_ALREADY_DONE_LOG, SEED_CSV_NOT_FOUND_LOG, SEED_FINISHED_LOG
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.managers.transaction_manager import build_transaction
from app.models.company import CompanyProfile
from app.models.account import BankAccount
from app.managers.card_manager import generate_cards
from app.services.demo_scenario import ensure_demo_extras, ensure_demo_scenario
from app.services.statement_parser import parse_bank_statement_csv

logger = logging.getLogger(__name__)


def _default_csv_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "memory", "reference", "sample-data", "pizzeria-amalfi-bank-statement-2025-v6.csv"
    )


async def seed_data():
    csv_path = settings.SEED_CSV_PATH or _default_csv_path()

    if not os.path.exists(csv_path):
        logger.warning(SEED_CSV_NOT_FOUND_LOG, csv_path)
        return

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        result = await session.execute(select(CompanyProfile).limit(1))
        existing_profile = result.scalar_one_or_none()
        if existing_profile:
            logger.info(SEED_ALREADY_DONE_LOG, existing_profile.name)
            await _add_demo_scenario(session)
            return

        logger.info("Seeding single-tenant company profile...")
        company = CompanyProfile(
            name="Pizzeria Amalfi",
            country="DE",
            base_currency="EUR",
            industry="Gastronomy",
            tax_identifier="DE123456789",
            settings={
                MIN_SAFETY_BUFFER_KEY: DEFAULT_MIN_SAFETY_BUFFER,
                "forecast_days_horizon": 90,
                "currency_risk_threshold": DEFAULT_CURRENCY_RISK_THRESHOLD,
                "owner_name": "Vincenzo Amalfi",
                "staff_count": 4,
            }
        )
        session.add(company)
        await session.flush()

        logger.info("Seeding primary bank account...")
        account = BankAccount(
            account_number="DE89370400440532013000",
            account_name="Pizzeria Amalfi Operative Account",
            bank_name="Commerzbank Frankfurt",
            bank_code="COBADEFFXXX",
            currency="EUR",
            current_balance=Decimal("33266.35"),  # End of 2025 balance
            overdraft_limit=Decimal("0.00"),     # Currently no line granted
            is_primary=True,
        )
        session.add(account)
        await session.flush()

        logger.info("Parsing statement from %s...", csv_path)
        with open(csv_path, "r", encoding="utf-8") as f:
            parsed_txs = parse_bank_statement_csv(f.read())

        logger.info("Inserting %d transactions...", len(parsed_txs))
        for tx in parsed_txs:
            session.add(build_transaction(account.id, tx))

        await session.flush()

        await ensure_demo_scenario(session, account)
        await ensure_demo_extras(session, account, company)
        await generate_cards(session)

        await session.commit()
        logger.info(SEED_FINISHED_LOG)


async def _add_demo_scenario(session) -> None:
    query = select(BankAccount).where(BankAccount.is_primary.is_(True)).order_by(BankAccount.created_at).limit(1)
    account = (await session.execute(query)).scalars().first()
    if not account:
        return

    await ensure_demo_scenario(session, account)
    company = (await session.execute(select(CompanyProfile).order_by(CompanyProfile.created_at).limit(1))).scalars().first()
    if company:
        await ensure_demo_extras(session, account, company)
    result = await generate_cards(session)
    logger.info("Agents created %d decision cards", result["created"])
    await session.commit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    asyncio.run(seed_data())
