import asyncio
import os
import sys
from decimal import Decimal
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.base import Base
from app.models.company import CompanyProfile
from app.models.account import BankAccount
from app.models.transaction import Transaction
from app.schemas.invoice import InvoiceValidateRequest
from app.services.invoice_validator import validate_invoice_logic


async def run_validation_test_suite():
    print("=" * 75)
    print("  TESTING INVOICE & RECEIPT VALIDATION MECHANIC (LLM TOOL ENGINE)")
    print("=" * 75)

    # In-memory SQLite async engine
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # 1. Setup mock company & historical ledger
        company = CompanyProfile(
            name="Pizzeria Amalfi",
            country="DE",
            base_currency="EUR",
            settings={"min_safety_buffer": 5000.0}
        )
        session.add(company)

        account = BankAccount(
            account_number="DE89370400440532013000",
            current_balance=Decimal("33266.35"),
            is_primary=True,
        )
        session.add(account)
        await session.flush()

        # Add historical transaction for Asimex with legitimate IBAN
        legit_tx = Transaction(
            account_id=account.id,
            booking_date=date(2025, 12, 10),
            amount=Decimal("-623.48"),
            currency="EUR",
            amount_base_currency=Decimal("-623.48"),
            counterparty_name="Asimex Wholesale Ltd",
            counterparty_account="DE33500105170011223344", # Known legitimate IBAN
            payment_reference="Invoice AS-69664 Food Delivery",
            metadata_payload={}
        )
        session.add(legit_tx)
        await session.commit()

        # -------------------------------------------------------------
        # Test Case 1: Legitimate invoice with Early Payment Discount (Skonto)
        # -------------------------------------------------------------
        print("\n[TEST 1] Legitimate Vendor Invoice with 3% Skonto:")
        req1 = InvoiceValidateRequest(
            invoice_number="AS-70100",
            issue_date=date(2026, 1, 10),
            due_date=date(2026, 2, 10),
            counterparty_name="Asimex Wholesale Ltd",
            counterparty_iban="DE33500105170011223344",
            net_amount=Decimal("1000.00"),
            tax_amount=Decimal("70.00"),  # 7% food VAT
            gross_amount=Decimal("1070.00"),
            currency="EUR",
            early_discount_percent=Decimal("3.00"),
            early_discount_days=10
        )
        report1 = await validate_invoice_logic(session, req1)
        print(f"  - Valid: {report1.is_valid} | Risk: {report1.risk_level} ({report1.risk_score}/100)")
        print(f"  - IBAN Status: {report1.iban_status}")
        print(f"  - Early Discount: Available={report1.early_discount.is_available}, Savings=€{report1.early_discount.savings_amount}")
        print(f"  - Executive Summary: {report1.executive_summary}")
        assert report1.is_valid, "Test 1 failed: should be valid"
        assert report1.iban_status == "VERIFIED_KNOWN", "Test 1 failed: IBAN should be verified"
        assert report1.early_discount and report1.early_discount.savings_amount == Decimal("32.10")

        # -------------------------------------------------------------
        # Test Case 2: Phishing Fraud / Changed IBAN Attack
        # -------------------------------------------------------------
        print("\n[TEST 2] Suspected Phishing / Changed IBAN Fraud:")
        req2 = InvoiceValidateRequest(
            invoice_number="AS-70200",
            issue_date=date(2026, 1, 15),
            due_date=date(2026, 2, 15),
            counterparty_name="Asimex Wholesale Ltd",
            counterparty_iban="DE99999999999999999999", # Different attacker IBAN!
            net_amount=Decimal("1000.00"),
            tax_amount=Decimal("70.00"),
            gross_amount=Decimal("1070.00"),
            currency="EUR"
        )
        report2 = await validate_invoice_logic(session, req2)
        print(f"  - Valid: {report2.is_valid} | Risk: {report2.risk_level} ({report2.risk_score}/100)")
        print(f"  - IBAN Status: {report2.iban_status}")
        critical_flags = [f.code for f in report2.flags if f.severity == "CRITICAL"]
        print(f"  - Critical Flags: {critical_flags}")
        assert not report2.is_valid, "Test 2 failed: should NOT be valid"
        assert "IBAN_MISMATCH_SUSPECTED_PHISHING" in critical_flags

        # -------------------------------------------------------------
        # Test Case 3: Math / Arithmetic Mismatch
        # -------------------------------------------------------------
        print("\n[TEST 3] Math Calculation Error (Net + Tax != Gross):")
        req3 = InvoiceValidateRequest(
            invoice_number="INV-BAD-MATH",
            issue_date=date(2026, 1, 15),
            due_date=date(2026, 2, 15),
            counterparty_name="Random Supplier",
            net_amount=Decimal("1000.00"),
            tax_amount=Decimal("190.00"),
            gross_amount=Decimal("1500.00"), # Error! Should be 1190
            currency="EUR"
        )
        report3 = await validate_invoice_logic(session, req3)
        print(f"  - Valid: {report3.is_valid} | Risk: {report3.risk_level} ({report3.risk_score}/100)")
        assert not report3.is_valid, "Test 3 failed: should fail math check"
        assert any(f.code == "ARITHMETIC_MISMATCH" for f in report3.flags)

        # -------------------------------------------------------------
        # Test Case 4: Duplicate Invoice (Already settled in ledger)
        # -------------------------------------------------------------
        print("\n[TEST 4] Duplicate Invoice (Already paid in bank ledger):")
        req4 = InvoiceValidateRequest(
            invoice_number="AS-69664", # Matches payment_reference in legit_tx
            issue_date=date(2026, 1, 15),
            due_date=date(2026, 2, 15),
            counterparty_name="Asimex Wholesale Ltd",
            counterparty_iban="DE33500105170011223344",
            net_amount=Decimal("582.69"),
            tax_amount=Decimal("40.79"),
            gross_amount=Decimal("623.48"),
            currency="EUR"
        )
        report4 = await validate_invoice_logic(session, req4)
        print(f"  - Valid: {report4.is_valid} | Risk: {report4.risk_level} ({report4.risk_score}/100)")
        print(f"  - Duplicate Detected: {report4.duplicate_detected}")
        assert report4.duplicate_detected, "Test 4 failed: duplicate should be detected"

        print("\n" + "=" * 75)
        print("  [✔] ALL INVOICE VALIDATION TEST CASES PASSED SUCCESSFULLY!")
        print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_validation_test_suite())
