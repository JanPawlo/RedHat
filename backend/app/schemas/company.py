from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

from app.const.company import (
    COMPANY_NAME_MAX_LENGTH,
    COUNTRY_MAX_LENGTH,
    DEFAULT_COMPANY_SETTINGS,
    INDUSTRY_MAX_LENGTH,
    TAX_IDENTIFIER_MAX_LENGTH,
)
from app.const.validation import CURRENCY_CODE_PATTERN


class CompanyProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=COMPANY_NAME_MAX_LENGTH)
    country: str = Field(default="DE", max_length=COUNTRY_MAX_LENGTH)
    base_currency: str = Field(default="EUR", pattern=CURRENCY_CODE_PATTERN)
    industry: Optional[str] = Field(default=None, max_length=INDUSTRY_MAX_LENGTH)
    tax_identifier: Optional[str] = Field(default=None, max_length=TAX_IDENTIFIER_MAX_LENGTH)
    settings: Dict[str, Any] = Field(default_factory=lambda: dict(DEFAULT_COMPANY_SETTINGS))


class CompanyProfileCreate(CompanyProfileBase):
    pass


class CompanyProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=COMPANY_NAME_MAX_LENGTH)
    country: Optional[str] = Field(default=None, max_length=COUNTRY_MAX_LENGTH)
    base_currency: Optional[str] = Field(default=None, pattern=CURRENCY_CODE_PATTERN)
    industry: Optional[str] = Field(default=None, max_length=INDUSTRY_MAX_LENGTH)
    tax_identifier: Optional[str] = Field(default=None, max_length=TAX_IDENTIFIER_MAX_LENGTH)
    settings: Optional[Dict[str, Any]] = None


class CompanyProfileResponse(CompanyProfileBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
