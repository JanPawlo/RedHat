from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any
from pydantic import BaseModel, ConfigDict


class LiquidityForecastBase(BaseModel):
    account_id: UUID
    forecast_date: date
    projected_balance: Decimal
    projected_inflows: Decimal = Decimal("0.00")
    projected_outflows: Decimal = Decimal("0.00")
    is_deficit: bool = False
    scenario_name: str = "baseline"
    drivers: Dict[str, Any] = {}


class LiquidityForecastCreate(LiquidityForecastBase):
    pass


class LiquidityForecastResponse(LiquidityForecastBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
