from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class CompanyProfileBase(BaseModel):
    name: str
    country: str = "DE"
    base_currency: str = "EUR"
    industry: Optional[str] = None
    tax_identifier: Optional[str] = None
    settings: Dict[str, Any] = {
        "min_safety_buffer": 5000.0,
        "forecast_days_horizon": 60,
        "currency_risk_threshold": 1000.0,
    }


class CompanyProfileCreate(CompanyProfileBase):
    pass


class CompanyProfileUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    base_currency: Optional[str] = None
    industry: Optional[str] = None
    tax_identifier: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class CompanyProfileResponse(CompanyProfileBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
