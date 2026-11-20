from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class TransactionBase(BaseModel):
    account_id: UUID
    booking_date: date
    value_date: Optional[date] = None
    amount: Decimal
    currency: str = "EUR"
    amount_base_currency: Decimal
    transaction_type: Optional[str] = None
    category: Optional[str] = None
    counterparty_name: Optional[str] = None
    counterparty_account: Optional[str] = None
    counterparty_bank_code: Optional[str] = None
    payment_reference: Optional[str] = None
    info: Optional[str] = None
    is_recurring: bool = False
    metadata_payload: Dict[str, Any] = {}


class TransactionCreate(TransactionBase):
    pass


class TransactionResponse(TransactionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
