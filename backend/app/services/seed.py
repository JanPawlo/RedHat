import asyncio
import os
import sys
from decimal import Decimal
from datetime import date
from sqlalchemy import select

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import AsyncSessionLocal, async_engine, Base
from app.models.company import CompanyProfile
from app.models.account import BankAccount
from app.models.transaction import Transaction
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
            balance_as_of=date(2025, 12, 31),
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

        await session.commit()
        print("Database seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed_data())
