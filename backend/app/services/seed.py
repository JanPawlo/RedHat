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
from app.const.demo import (
    DEMO_COUNTRY,
    DEMO_CURRENCY,
    DEMO_PROFILE_CSV_DIRECTORY,
    DEMO_PROFILE_FILES,
    DEMO_PROFILES,
)
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


def _profile_csv_path(profile_name: str) -> str:
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(backend_root, DEMO_PROFILE_CSV_DIRECTORY, DEMO_PROFILE_FILES[profile_name])


async def seed_data():
    profile_name = settings.SEED_PROFILE
    profile = DEMO_PROFILES.get(profile_name)
    if not profile:
        logger.error("Unknown demo profile '%s'; available profiles: %s", profile_name, ", ".join(DEMO_PROFILES))
        return

    csv_path = settings.SEED_CSV_PATH or _profile_csv_path(profile_name)

    if not os.path.exists(csv_path):
        logger.warning(SEED_CSV_NOT_FOUND_LOG, csv_path)
        return

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        query = select(CompanyProfile).order_by(CompanyProfile.created_at).limit(1)
        existing_profile = (await session.execute(query)).scalars().first()
        if existing_profile:
            logger.info(SEED_ALREADY_DONE_LOG, existing_profile.name)
            return

        with open(csv_path, "r", encoding="utf-8") as f:
            parsed_txs = parse_bank_statement_csv(f.read())
        if not parsed_txs:
            logger.warning("Demo statement '%s' contains no transactions", csv_path)
            return

        account_number = parsed_txs[0]["account_number"]
        if any(tx["account_number"] != account_number for tx in parsed_txs):
            logger.error("Demo statement '%s' contains more than one account", csv_path)
            return

        balance_as_of = max(tx["booking_date"] for tx in parsed_txs)

        logger.info("Seeding single-tenant company profile...")
        company = CompanyProfile(
            name=profile["company_name"],
            country=DEMO_COUNTRY,
            base_currency=DEMO_CURRENCY,
            industry=profile["industry"],
            tax_identifier=None,
            settings={
                MIN_SAFETY_BUFFER_KEY: DEFAULT_MIN_SAFETY_BUFFER,
                "forecast_days_horizon": 90,
                "currency_risk_threshold": DEFAULT_CURRENCY_RISK_THRESHOLD,
                "owner_name": profile["owner_name"],
                "staff_count": profile["staff_count"],
            }
        )
        session.add(company)
        await session.flush()

        logger.info("Seeding primary bank account...")
        account = BankAccount(
            account_number=account_number,
            account_name=profile["account_name"],
            bank_name=profile["bank_name"],
            bank_code=None,
            currency=DEMO_CURRENCY,
            current_balance=profile["balance"],
            balance_as_of=balance_as_of,
            overdraft_limit=Decimal("0.00"),     # Currently no line granted
            is_primary=True,
        )
        session.add(account)
        await session.flush()

        logger.info("Inserting %d transactions...", len(parsed_txs))
        for tx in parsed_txs:
            session.add(build_transaction(account.id, tx))

        await session.flush()

        await ensure_demo_scenario(session, account, profile_name)
        await ensure_demo_extras(session, account, company, profile_name)
        await generate_cards(session)

        await session.commit()
        logger.info(SEED_FINISHED_LOG)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    asyncio.run(seed_data())
