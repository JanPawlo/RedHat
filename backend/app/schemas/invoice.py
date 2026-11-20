from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ValidationFlag(BaseModel):
    code: str = Field(..., description="Unique flag code (e.g. IBAN_MISMATCH, DUPLICATE_INVOICE, ARITHMETIC_ERROR)")
    severity: str = Field(..., description="Severity level: 'INFO', 'WARNING', 'CRITICAL'")
    title: str = Field(..., description="Short human-readable title")
    description: str = Field(..., description="Detailed explanation of the issue or insight")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Concrete numbers or historical references supporting this flag")


class InvoiceValidateRequest(BaseModel):
    """
    Schema for validating an invoice or receipt.
    Designed for easy tool-calling by LLMs (e.g. Qwen, Granite, OpenAI API).
    """
    invoice_number: str = Field(..., description="Invoice or receipt number (e.g. 'INV-2025-089' or 'AS-69664')")
    invoice_type: str = Field("incoming_expense", description="'incoming_expense', 'outgoing_revenue', or 'receipt'")
    issue_date: date = Field(..., description="Date invoice was issued (YYYY-MM-DD)")
    due_date: date = Field(..., description="Payment due date (YYYY-MM-DD)")
    counterparty_name: str = Field(..., description="Vendor, supplier or issuer name (e.g. 'Asimex Wholesale Ltd')")
    counterparty_iban: Optional[str] = Field(None, description="Bank account IBAN stated on the invoice")
    counterparty_tax_id: Optional[str] = Field(None, description="Tax ID / VAT / NIP / Steuernummer")
    counterparty_bic: Optional[str] = Field(None, description="Bank BIC / SWIFT code")
    
    net_amount: Decimal = Field(..., description="Net amount before VAT/tax")
    tax_amount: Decimal = Field(Decimal("0.00"), description="VAT / tax amount")
    gross_amount: Decimal = Field(..., description="Total gross payable amount")
    currency: str = Field("EUR", description="Three-letter currency code (EUR, PLN, CHF, USD)")
    
    early_discount_percent: Optional[Decimal] = Field(None, description="Early payment cash discount percent (e.g. 3.00 for 3% Skonto)")
    early_discount_days: Optional[int] = Field(None, description="Number of days from issue_date to qualify for early discount")
    
    line_items: List[Dict[str, Any]] = Field(default_factory=list, description="Optional itemized products/services for price checking")
    description: Optional[str] = Field(None, description="General invoice notes or description")


class EarlyDiscountOpportunity(BaseModel):
    is_available: bool
    discount_percent: Decimal
    deadline_date: date
    savings_amount: Decimal
    effective_payable: Decimal
    is_liquidity_safe: bool
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
    risk_level: str = Field(..., description="'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL'")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score from 0 (completely safe) to 100 (high probability of fraud/error)")
    
    # Specific check verdicts
    arithmetic_valid: bool
    duplicate_detected: bool
    iban_status: str = Field(..., description="'VERIFIED_KNOWN', 'NEW_COUNTERPARTY', or 'MISMATCH_ALERT'")
    price_anomaly_detected: bool
    liquidity_safe: bool
    
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
