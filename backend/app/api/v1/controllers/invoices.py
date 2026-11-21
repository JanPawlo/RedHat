from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import not_found
from app.const.messages import ACCOUNT_NOT_FOUND, INVOICE_NOT_FOUND
from app.const.pagination import DEFAULT_PAGE_LIMIT, INVOICES_MAX_LIMIT
from app.managers import invoice_manager
from app.managers.invoice_manager import InvoiceAccountNotFoundError
from app.models.user import User
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceResponse,
    InvoiceValidateRequest,
    ValidationReport,
)

invoices_router = APIRouter(prefix="/invoices", tags=["Invoices & Verification"])


@invoices_router.post(
    "/validate",
    response_model=ValidationReport,
    summary="Validate an invoice/receipt and detect anomalies (LLM Tool Target)",
)
async def validate_invoice(
    payload: InvoiceValidateRequest,
    auto_create_card: bool = Query(False, description="Whether to also save a swipe decision card on warnings or discounts"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    Validates an incoming invoice or receipt against:
    - Arithmetic and VAT rate integrity
    - Duplicate detection (both stored invoices and bank transactions)
    - Vendor IBAN verification (anti-phishing fraud detection)
    - Spending spikes compared to vendor payment history
    - Cash flow liquidity impact (overdraft and safety buffer violation)
    - Early payment cash discounts (Skonto)
    """
    return await invoice_manager.validate_invoice(db, payload, auto_create_card)


@invoices_router.get(
    "/tools/llm-schema",
    summary="Get OpenAI/vLLM tool definition schema for invoice validation",
)
async def get_llm_tool_schema(current_user: User = Depends(get_current_user)):
    """
    Returns OpenAI/vLLM function tool declaration for `validate_invoice`.
    Can be passed directly into LLM agent completion calls on OpenShift AI (vLLM / Qwen / Granite).
    """
    return invoice_manager.get_llm_tool_schema()


@invoices_router.post(
    "",
    response_model=InvoiceResponse,
    summary="Register and validate an invoice in the system",
)
async def create_and_validate_invoice(
    payload: InvoiceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    try:
        return await invoice_manager.create_and_validate_invoice(db, payload)
    except InvoiceAccountNotFoundError:
        raise not_found(ACCOUNT_NOT_FOUND)


@invoices_router.get(
    "",
    response_model=List[InvoiceResponse],
    summary="List stored invoices",
)
async def list_invoices(
    validation_status: Optional[str] = None,
    counterparty_name: Optional[str] = None,
    is_paid: Optional[bool] = None,
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=INVOICES_MAX_LIMIT),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    return await invoice_manager.list_invoices(db, validation_status, counterparty_name, is_paid, limit, offset)


@invoices_router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get invoice details and validation outcome",
)
async def get_invoice(
    invoice_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    invoice = await invoice_manager.get_invoice(db, invoice_id)
    if not invoice:
        raise not_found(INVOICE_NOT_FOUND)

    return invoice
