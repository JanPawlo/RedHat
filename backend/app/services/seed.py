import asyncio
import logging
import os
import sys
from decimal import Decimal
from sqlalchemy import select

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.const.action import ACTION_STATUS_PENDING, EXECUTION_MODE_SIMULATED
from app.const.app import LOG_FORMAT
from app.const.company import DEFAULT_CURRENCY_RISK_THRESHOLD, DEFAULT_MIN_SAFETY_BUFFER, MIN_SAFETY_BUFFER_KEY
from app.const.messages import SEED_ALREADY_DONE_LOG, SEED_CSV_NOT_FOUND_LOG, SEED_FINISHED_LOG
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.managers.transaction_manager import build_transaction
from app.models.company import CompanyProfile
from app.models.account import BankAccount
from app.models.action import AgentAction
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

        logger.info("Creating explainable AI Agent Action for June seasonal liquidity crisis...")
        action = AgentAction(
            title="Seasonal Liquidity Buffer: Projected June Deficit Warning",
            agent_type="liquidity_guard",
            trigger_reason=(
                "Cash flow forecasting predicts an account balance drop to -€22,097.60 on July 3, 2025 "
                "due to the 3-week planned summer restaurant shutdown while fixed costs (rent, wages, taxes) continue."
            ),
            recommended_action="activate_commerzbank_credit_line",
            target_amount=Decimal("25000.00"),
            currency="EUR",
            explanation=(
                "During June, zero customer POS revenue will be settled, while fixed outflows total approx €17,350 "
                "(Wages €8,600, Rent €3,800, Health insurance €2,650, Tax prepayments €1,150, Swiss partner transfer €4,360). "
                "Without intervention, your account will enter deep unauthorized overdraft. "
                "We recommend pre-activating a Commerzbank Revolving Credit Limit of €25,000 before June 1st to maintain liquidity."
            ),
            impact_simulation={
                "projected_trough_without_action": -22097.60,
                "projected_trough_with_credit_line": 2902.40,
                "estimated_monthly_interest_cost": 85.00,
                "recovery_horizon_date": "2025-09-15",
            },
            status=ACTION_STATUS_PENDING,
            execution_mode=EXECUTION_MODE_SIMULATED,
            user_feedback=None,
        )
        session.add(action)

        await session.commit()
        logger.info(SEED_FINISHED_LOG)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    asyncio.run(seed_data())
