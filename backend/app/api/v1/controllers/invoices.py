from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import not_found
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_INVOICES
from app.const.messages import ACCOUNT_NOT_FOUND, INVOICE_NOT_FOUND
from app.const.pagination import DEFAULT_PAGE_LIMIT, INVOICES_MAX_LIMIT
from app.managers import card_manager, invoice_manager
from app.managers.invoice_manager import InvoiceAccountNotFoundError
from app.models.user import User
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceResponse,
    InvoiceValidateRequest,
    ValidationReport,
)

invoices_router = APIRouter(prefix="/invoices", tags=[TAG_INVOICES], responses=RESPONSE_UNAUTHORIZED)


@invoices_router.post(
    "/validate",
    response_model=ValidationReport,
    summary="Check an invoice without saving it",
)
async def validate_invoice(
    payload: InvoiceValidateRequest,
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

    Returns flags with evidence, a risk score 0–100, a plain-language summary and, when relevant, a ready decision card.
    The invoice itself is not stored; use `POST /invoices` for that.
    """
    return await invoice_manager.validate_invoice(db, payload)


@invoices_router.get(
    "/tools/llm-schema",
    summary="Tool definition of the invoice check for LLM agents",
)
async def get_llm_tool_schema(current_user: User = Depends(get_current_user)):
    """
    Returns the OpenAI/vLLM function tool declaration for `validate_invoice`.
    Can be passed directly into LLM agent completion calls on OpenShift AI (vLLM / Qwen / Granite).
    Not needed by the frontend.
    """
    return invoice_manager.get_llm_tool_schema()


@invoices_router.post(
    "",
    response_model=InvoiceResponse,
    summary="Save an invoice and check it",
    responses={404: {"description": "The given account_id does not exist"}},
)
async def create_and_validate_invoice(
    payload: InvoiceCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    Runs the same checks as `/validate` and stores the invoice with its result.
    Unpaid invoices are included in the cash forecast on their due date
    (`incoming_expense` as money out, `outgoing_revenue` as money in). The decision cards are refreshed in the
    background after the invoice is saved (the model writes their text), so `GET /cards` shows them a little later.
    """
    try:
        invoice = await invoice_manager.create_and_validate_invoice(db, payload)
    except InvoiceAccountNotFoundError:
        raise not_found(ACCOUNT_NOT_FOUND)

    await db.commit()  # the background refresh uses its own session and must see this invoice
    background_tasks.add_task(card_manager.refresh_cards_in_background, payload.account_id)
    return invoice


@invoices_router.get(
    "",
    response_model=List[InvoiceResponse],
    summary="List saved invoices",
)
async def list_invoices(
    validation_status: Optional[str] = Query(None, description="valid, warning or flagged_risk"),
    counterparty_name: Optional[str] = Query(None, description="Part of the counterparty name"),
    is_paid: Optional[bool] = Query(None, description="true = paid, false = still open"),
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=INVOICES_MAX_LIMIT),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """Newest issue date first."""
    return await invoice_manager.list_invoices(db, validation_status, counterparty_name, is_paid, limit, offset)


@invoices_router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get an invoice with its check result",
    responses={404: {"description": "Invoice not found"}},
)
async def get_invoice(
    invoice_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """`validation_details` holds the full report from the check (flags, evidence, card)."""
    invoice = await invoice_manager.get_invoice(db, invoice_id)
    if not invoice:
        raise not_found(INVOICE_NOT_FOUND)

    return invoice
