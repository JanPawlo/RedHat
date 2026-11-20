import asyncio
import os
import sys
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy import select

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import AsyncSessionLocal, async_engine, Base
from app.models.company import CompanyProfile
from app.models.account import BankAccount
from app.models.transaction import Transaction
from app.models.forecast import LiquidityForecast
from app.models.action import AgentAction
from app.services.statement_parser import parse_bank_statement_csv


async def seed_data():
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "materials", "sample-data", "pizzeria-amalfi-bank-statement-2025-v6.csv"
    )

    if not os.path.exists(csv_path):
        print(f"Warning: sample CSV not found at {csv_path}")
        return

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        result = await session.execute(select(CompanyProfile).limit(1))
        existing_profile = result.scalar_one_or_none()
        if existing_profile:
            print(f"Database already seeded with company: {existing_profile.name}")
            return

        print("Seeding single-tenant company profile...")
        company = CompanyProfile(
            name="Pizzeria Amalfi",
            country="DE",
            base_currency="EUR",
            industry="Gastronomy",
            tax_identifier="DE123456789",
            settings={
                "min_safety_buffer": 5000.0,
                "forecast_days_horizon": 90,
                "currency_risk_threshold": 1000.0,
                "owner_name": "Vincenzo Amalfi",
                "staff_count": 4,
            }
        )
        session.add(company)
        await session.flush()

        print("Seeding primary bank account...")
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

        print(f"Parsing statement from {csv_path}...")
        with open(csv_path, "r", encoding="utf-8") as f:
            parsed_txs = parse_bank_statement_csv(f.read())

        print(f"Inserting {len(parsed_txs)} transactions...")
        for tx in parsed_txs:
            db_tx = Transaction(
                account_id=account.id,
                booking_date=tx["booking_date"],
                value_date=tx["value_date"],
                amount=tx["amount"],
                currency=tx["currency"],
                amount_base_currency=tx["amount_base_currency"],
                transaction_type=tx["transaction_type"],
                category=tx["category"],
                counterparty_name=tx["counterparty_name"],
                counterparty_account=tx["counterparty_account"],
                counterparty_bank_code=tx["counterparty_bank_code"],
                payment_reference=tx["payment_reference"],
                info=tx["info"],
                is_recurring=tx["is_recurring"],
                metadata_payload=tx["metadata_payload"],
            )
            session.add(db_tx)

        print("Creating explainable AI Agent Action for June seasonal liquidity crisis...")
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
            status="pending",
            execution_mode="simulated",
            user_feedback=None,
        )
        session.add(action)

        await session.commit()
        print("Database seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed_data())
