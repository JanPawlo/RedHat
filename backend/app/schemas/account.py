from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class BankAccountBase(BaseModel):
    account_number: str
    account_name: str = "Main Operating Account"
    bank_name: str = "Commerzbank"
    bank_code: Optional[str] = None
    currency: str = "EUR"
    current_balance: Decimal = Decimal("0.00")
    balance_as_of: Optional[date] = None
    overdraft_limit: Decimal = Decimal("0.00")
    is_primary: bool = True


class BankAccountCreate(BankAccountBase):
    pass


class BankAccountResponse(BankAccountBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BankBalanceUpdate(BaseModel):
    current_balance: Decimal = Field(..., ge=Decimal("-9999999999999.99"), le=Decimal("9999999999999.99"))
    balance_as_of: date
