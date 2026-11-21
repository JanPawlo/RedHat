from decimal import Decimal
from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import String, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.forecast import LiquidityForecast
    from app.models.transaction import Transaction


class BankAccount(Base, UUIDMixin, TimestampMixin):
    """
    Bank account belonging to the local company.
    Supports primary operational accounts, multi-currency accounts, and credit limits.
    """
    __tablename__ = "bank_accounts"

    account_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    account_name: Mapped[str] = mapped_column(String(128), default="Main Operating Account", nullable=False)
    bank_name: Mapped[str] = mapped_column(String(128), default="Commerzbank", nullable=False)
    bank_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # BIC / BLZ
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    
    current_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    overdraft_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="desc(Transaction.booking_date)"
    )
    forecasts: Mapped[List["LiquidityForecast"]] = relationship(
        "LiquidityForecast",
        back_populates="account",
        cascade="all, delete-orphan"
    )
