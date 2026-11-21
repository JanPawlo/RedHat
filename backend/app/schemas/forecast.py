from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.const.docs import EXAMPLE_SIMULATION
from app.const.forecast import CHANGE_LABEL_MAX_LENGTH, SIMULATION_MAX_CHANGES
from app.const.validation import AMOUNT_DECIMAL_PLACES, AMOUNT_MAX_DIGITS


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


class CashChangeRequest(BaseModel):
    on_date: date
    amount: Decimal = Field(..., max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, description="Signed amount: + money in, - money out")
    label: str = Field(..., min_length=1, max_length=CHANGE_LABEL_MAX_LENGTH)


class SimulationRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_SIMULATION]})

    changes: List[CashChangeRequest] = Field(..., min_length=1, max_length=SIMULATION_MAX_CHANGES)


class DriverResponse(BaseModel):
    label: str
    amount: Decimal


class ForecastDayResponse(BaseModel):
    day: date
    balance: Decimal
    inflows: Decimal
    outflows: Decimal
    drivers: List[DriverResponse]


class IndicatorsResponse(BaseModel):
    lowest_balance: Decimal
    lowest_balance_date: date
    first_below_buffer_date: Optional[date]
    first_below_zero_date: Optional[date]
    days_to_buffer_breach: Optional[int]
    runway_months: Optional[Decimal] = Field(None, description="None when the balance is not falling")
    free_cash: Decimal = Field(..., description="Lowest balance in the horizon minus the safety buffer; negative means a shortfall")


class ScenarioResponse(BaseModel):
    name: str
    revenue_factor: Decimal
    indicators: IndicatorsResponse
    days: List[ForecastDayResponse]


class RecurringPaymentResponse(BaseModel):
    counterparty: str
    category: str
    amount: Decimal
    interval_months: int
    day_of_month: int
    last_date: date
    occurrences: int


class RevenueModelResponse(BaseModel):
    weekday_inflow: List[Decimal] = Field(..., description="Average revenue per weekday, Monday first")
    variable_cost_ratio: Decimal
    month_factors: Dict[int, Decimal]
    lookback_factor: Decimal
    volatility: Decimal


class ForecastResponse(BaseModel):
    account_id: UUID
    currency: str
    as_of: date
    opening_balance: Decimal
    safety_buffer: Decimal
    horizon_days: int
    confidence: Decimal = Field(..., description="Share of revenue scenarios in which the balance stays above the buffer")
    revenue_model: RevenueModelResponse
    recurring: List[RecurringPaymentResponse]
    scenarios: Dict[str, ScenarioResponse]
    skipped_invoices: List[str] = Field(default_factory=list, description="Unpaid invoices left out because their currency differs from the account")


class SimulationResponse(BaseModel):
    baseline: ForecastResponse
    simulated: ForecastResponse
    lowest_balance_change: Decimal
