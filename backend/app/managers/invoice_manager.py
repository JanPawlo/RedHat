from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.const.invoice import (
    LLM_TOOL_DESCRIPTION,
    LLM_TOOL_NAME,
    LLM_TOOL_TYPE,
    RISK_LEVEL_CRITICAL,
    RISK_LEVEL_HIGH,
    VALIDATION_STATUS_FLAGGED_RISK,
    VALIDATION_STATUS_VALID,
    VALIDATION_STATUS_WARNING,
)
from app.const.sql import LIKE_ESCAPE_CHAR
from app.core.sql import contains_pattern
from app.managers.account_manager import get_account
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreate, InvoiceValidateRequest, ValidationReport
from app.services.invoice_validator import validate_invoice_logic


class InvoiceAccountNotFoundError(Exception):
    pass


async def validate_invoice(db: AsyncSession, payload: InvoiceValidateRequest) -> ValidationReport:
    return await validate_invoice_logic(db=db, req=payload)


def get_llm_tool_schema() -> Dict[str, Any]:
    schema = InvoiceValidateRequest.model_json_schema()

    return {
        "type": LLM_TOOL_TYPE,
        "function": {
            "name": LLM_TOOL_NAME,
            "description": LLM_TOOL_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", []),
            },
        },
    }


def _resolve_validation_status(risk_level: str) -> str:
    if risk_level == RISK_LEVEL_CRITICAL:
        return VALIDATION_STATUS_FLAGGED_RISK
    if risk_level == RISK_LEVEL_HIGH:
        return VALIDATION_STATUS_WARNING
    return VALIDATION_STATUS_VALID


def _build_invoice(payload: InvoiceCreate, report: ValidationReport) -> Invoice:
    return Invoice(
        **payload.model_dump(),
        is_validated=True,
        validation_status=_resolve_validation_status(report.risk_level),
        risk_score=report.risk_score,
        validation_details=report.model_dump(mode="json"),
    )


async def _ensure_account_exists(db: AsyncSession, account_id: Optional[UUID]) -> None:
    if account_id and not await get_account(db, account_id):
        raise InvoiceAccountNotFoundError()


async def create_and_validate_invoice(db: AsyncSession, payload: InvoiceCreate) -> Invoice:
    await _ensure_account_exists(db, payload.account_id)

    report = await validate_invoice_logic(db=db, req=payload)

    invoice = _build_invoice(payload, report)
    db.add(invoice)

    await db.flush()
    await db.refresh(invoice)
    return invoice


async def list_invoices(
    db: AsyncSession,
    validation_status: Optional[str],
    counterparty_name: Optional[str],
    is_paid: Optional[bool],
    limit: int,
    offset: int,
) -> List[Invoice]:
    query = select(Invoice).order_by(desc(Invoice.issue_date))

    if validation_status:
        query = query.where(Invoice.validation_status == validation_status)
    if counterparty_name:
        query = query.where(Invoice.counterparty_name.ilike(contains_pattern(counterparty_name), escape=LIKE_ESCAPE_CHAR))
    if is_paid is not None:
        query = query.where(Invoice.is_paid == is_paid)

    result = await db.execute(query.offset(offset).limit(limit))
    return list(result.scalars().all())


async def get_invoice(db: AsyncSession, invoice_id: UUID) -> Optional[Invoice]:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    return result.scalar_one_or_none()
