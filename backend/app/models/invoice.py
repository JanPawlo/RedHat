import uuid
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any
from sqlalchemy import String, Numeric, Date, Boolean, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class Invoice(Base, UUIDMixin, TimestampMixin):
    """
    Invoice or receipt received or issued by the company.
    Stores invoice header data, validation outcomes, and links to settled transactions.
    """
    __tablename__ = "invoices"

    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Identifiers
    invoice_number: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    invoice_type: Mapped[str] = mapped_column(String(32), default="incoming_expense", index=True, nullable=False)
    # Types: 'incoming_expense', 'outgoing_revenue', 'receipt', 'credit_note'

    # Dates
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)

    # Counterparty details
    counterparty_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    counterparty_tax_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True) # NIP / Steuernummer / VAT ID
    counterparty_iban: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    counterparty_bic: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Financial breakdown
    net_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)

    # Early payment terms (Skonto)
    early_discount_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True) # e.g. 3.00 for 3%
    early_discount_days: Mapped[Optional[int]] = mapped_column(nullable=True) # e.g. within 10 days of issue

    # Automated Validation & Fraud Detection Status
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    # Statuses: 'pending', 'valid', 'warning', 'flagged_risk', 'rejected'
    risk_score: Mapped[int] = mapped_column(default=0, nullable=False) # 0 to 100
    validation_details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Settlement tracking
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    paid_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True
    )

    # Description and arbitrary OCR / KSeF / ERP payload
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    account: Mapped[Optional["BankAccount"]] = relationship("BankAccount")
    paid_transaction: Mapped[Optional["Transaction"]] = relationship("Transaction")
