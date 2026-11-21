from typing import Optional, Dict, Any
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.const.company import DEFAULT_COMPANY_SETTINGS
from app.core.database import Base
from app.models.base import JSONType, UUIDMixin, TimestampMixin


class CompanyProfile(Base, UUIDMixin, TimestampMixin):
    """
    Local company profile for this CFO instance.
    Stores company identity, accounting baseline, and CFO agent preferences.
    """
    __tablename__ = "company_profile"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(10), default="DE", nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tax_identifier: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Agent operational settings (e.g. minimum safety buffer, auto-alert thresholds)
    settings: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        default=lambda: dict(DEFAULT_COMPANY_SETTINGS),
        nullable=False
    )
