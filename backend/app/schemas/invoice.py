from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.const.invoice import (
    COUNTERPARTY_BIC_MAX_LENGTH,
    COUNTERPARTY_IBAN_MAX_LENGTH,
    COUNTERPARTY_NAME_MAX_LENGTH,
    COUNTERPARTY_TAX_ID_MAX_LENGTH,
    DISCOUNT_DAYS_MAX,
    DISCOUNT_PERCENT_MAX,
    DISCOUNT_PERCENT_MAX_DIGITS,
    IBAN_STATUSES,
    INVOICE_NUMBER_MAX_LENGTH,
    INVOICE_TYPE_INCOMING_EXPENSE,
    INVOICE_TYPES,
    RISK_LEVELS,
    RISK_SCORE_MAX,
    SEVERITIES,
)
from app.const.messages import DUE_DATE_BEFORE_ISSUE_DATE
from app.const.validation import AMOUNT_DECIMAL_PLACES, AMOUNT_MAX_DIGITS, CURRENCY_CODE_PATTERN

InvoiceType = Literal[INVOICE_TYPES]
RiskLevel = Literal[RISK_LEVELS]
Severity = Literal[SEVERITIES]
IbanStatus = Literal[IBAN_STATUSES]


class ValidationFlag(BaseModel):
    code: str = Field(..., description="Unique flag code (e.g. IBAN_MISMATCH, DUPLICATE_INVOICE, ARITHMETIC_ERROR)")
    severity: Severity = Field(..., description="Severity level: 'INFO', 'WARNING', 'CRITICAL'")
    title: str = Field(..., description="Short human-readable title")
    description: str = Field(..., description="Detailed explanation of the issue or insight")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Concrete numbers or historical references supporting this flag")


class InvoiceValidateRequest(BaseModel):
    """
    Schema for validating an invoice or receipt.
    Designed for easy tool-calling by LLMs (e.g. Qwen, Granite, OpenAI API).
    """
    invoice_number: str = Field(..., min_length=1, max_length=INVOICE_NUMBER_MAX_LENGTH, description="Invoice or receipt number (e.g. 'INV-2025-089' or 'AS-69664')")
    invoice_type: InvoiceType = Field(INVOICE_TYPE_INCOMING_EXPENSE, description="'incoming_expense', 'outgoing_revenue', 'receipt' or 'credit_note'")
    issue_date: date = Field(..., description="Date invoice was issued (YYYY-MM-DD)")
    due_date: date = Field(..., description="Payment due date (YYYY-MM-DD), not earlier than issue_date")
    counterparty_name: str = Field(..., min_length=1, max_length=COUNTERPARTY_NAME_MAX_LENGTH, description="Vendor, supplier or issuer name (e.g. 'Asimex Wholesale Ltd')")
    counterparty_iban: Optional[str] = Field(None, max_length=COUNTERPARTY_IBAN_MAX_LENGTH, description="Bank account IBAN stated on the invoice")
    counterparty_tax_id: Optional[str] = Field(None, max_length=COUNTERPARTY_TAX_ID_MAX_LENGTH, description="Tax ID / VAT / NIP / Steuernummer")
    counterparty_bic: Optional[str] = Field(None, max_length=COUNTERPARTY_BIC_MAX_LENGTH, description="Bank BIC / SWIFT code")

    net_amount: Decimal = Field(..., ge=0, max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, description="Net amount before VAT/tax")
    tax_amount: Decimal = Field(Decimal("0.00"), ge=0, max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, description="VAT / tax amount")
    gross_amount: Decimal = Field(..., ge=0, max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, description="Total gross payable amount")
    currency: str = Field("EUR", pattern=CURRENCY_CODE_PATTERN, description="Three-letter uppercase currency code (EUR, PLN, CHF, USD)")

    early_discount_percent: Optional[Decimal] = Field(None, ge=0, le=DISCOUNT_PERCENT_MAX, max_digits=DISCOUNT_PERCENT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, description="Early payment cash discount percent (e.g. 3.00 for 3% Skonto)")
    early_discount_days: Optional[int] = Field(None, ge=0, le=DISCOUNT_DAYS_MAX, description="Number of days from issue_date to qualify for early discount")

    description: Optional[str] = Field(None, description="General invoice notes or description")

    @model_validator(mode="after")
    def _due_date_not_before_issue_date(self) -> "InvoiceValidateRequest":
        if self.due_date < self.issue_date:
            raise ValueError(DUE_DATE_BEFORE_ISSUE_DATE)
        return self


class EarlyDiscountOpportunity(BaseModel):
    is_available: bool
    discount_percent: Decimal
    deadline_date: date
    savings_amount: Decimal
    effective_payable: Decimal
    is_liquidity_safe: Optional[bool] = Field(None, description="None when there is no bank account data to check against")
    reasoning: str


class ValidationReport(BaseModel):
    """
    Structured outcome returned by the validation engine.
    The LLM uses this report to explain the findings to the owner and decide whether to approve or flag.
    """
    invoice_number: str
    counterparty_name: str
    gross_amount: Decimal
    currency: str

    is_valid: bool = Field(..., description="Whether the invoice passes all critical checks without blocking flags")
    risk_level: RiskLevel = Field(..., description="'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL'")
    risk_score: int = Field(..., ge=0, le=RISK_SCORE_MAX, description="Risk score from 0 (completely safe) to 100 (high probability of fraud/error)")

    arithmetic_valid: bool
    duplicate_detected: bool
    iban_status: IbanStatus = Field(..., description="'VERIFIED_KNOWN', 'NEW_COUNTERPARTY', or 'MISMATCH_ALERT'")
    price_anomaly_detected: bool
    liquidity_safe: Optional[bool] = Field(None, description="None when there is no bank account data to check against")

    flags: List[ValidationFlag] = Field(default_factory=list)
    early_discount: Optional[EarlyDiscountOpportunity] = None

    executive_summary: str = Field(..., description="Plain-language summary of the validation for the business owner")
    suggested_action_card: Optional[Dict[str, Any]] = Field(None, description="Decision card ready to be rendered in the swipe deck")


class InvoiceCreate(InvoiceValidateRequest):
    account_id: Optional[UUID] = None
    raw_metadata: Dict[str, Any] = {}


class InvoiceResponse(BaseModel):
    id: UUID
    account_id: Optional[UUID]
    invoice_number: str
    invoice_type: str
    issue_date: date
    due_date: date
    counterparty_name: str
    counterparty_tax_id: Optional[str]
    counterparty_iban: Optional[str]
    net_amount: Decimal
    tax_amount: Decimal
    gross_amount: Decimal
    currency: str
    is_validated: bool
    validation_status: str
    risk_score: int
    validation_details: Dict[str, Any]
    is_paid: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
