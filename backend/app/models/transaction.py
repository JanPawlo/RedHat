import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Dict, Any
from sqlalchemy import String, Numeric, Date, Boolean, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import JSONType, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import BankAccount


class Transaction(Base, UUIDMixin, TimestampMixin):
    """
    Financial transaction on a company bank account.
    Core fields handle standard statement ledgers, while `metadata_payload` provides
    extensibility for arbitrary extra data (e.g. ERP tags, raw CSV columns, invoice refs).
    """
    __tablename__ = "transactions"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    booking_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    value_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Financial values (signed: positive for inflows, negative for outflows)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    
    # Amount normalized in company's base currency (e.g. converting CHF transfers to EUR)
    amount_base_currency: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    # Classification & Categorization
    transaction_type: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    # Examples: 'revenue_pos', 'supplier', 'salary', 'tax', 'rent', 'fx_transfer', 'utility'

    # Counterparty Details
    counterparty_name: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    counterparty_account: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    counterparty_bank_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # References & Raw Information
    payment_reference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Extensible JSON store for additional data not captured in fixed columns
    metadata_payload: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)

    # Relationships
    account: Mapped["BankAccount"] = relationship("BankAccount", back_populates="transactions")


# Index for date-range liquidity queries
Index("ix_transactions_account_date", Transaction.account_id, Transaction.booking_date)
