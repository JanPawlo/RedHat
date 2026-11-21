import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import bad_request, not_found
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_STATEMENTS
from app.const.messages import ACCOUNT_NOT_FOUND, STATEMENT_IMPORT_REJECTED_LOG
from app.const.statement import IMPORT_STATUS_SUCCESS, STATEMENT_MAX_BYTES
from app.managers import statement_manager
from app.managers.statement_manager import StatementAccountNotFoundError, StatementImportError
from app.models.user import User
from app.services.statement_parser import StatementParseError

logger = logging.getLogger(__name__)

statements_router = APIRouter(prefix="/statements", tags=[TAG_STATEMENTS], responses=RESPONSE_UNAUTHORIZED)


@statements_router.post(
    "/upload/csv",
    summary="Import a bank statement CSV",
    responses={
        400: {"description": "Not a CSV, too large, bad encoding or a bad row (the message names the row)"},
        404: {"description": "The given account_id does not exist"},
    },
)
async def upload_bank_statement(
    file: UploadFile = File(..., description="Bank statement in the German online banking layout (';' separated, see sample data)"),
    account_id: Optional[UUID] = Query(None, description="Import into this account; otherwise the account number from the file is used (a new account is created if needed)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    Parses the CSV into transactions, assigns categories and updates the account balance.

    - Columns: Account Number, Booking Date, Value Date, Transaction Type, Payment Reference,
      Beneficiary/Payer, Counterparty Account, Bank Code, Amount, Currency, Info.
    - `.csv` only, max 5 MB, UTF-8 / cp1252 / cp1250.
    - Rows already imported (same date, amount, reference and counterparty) are skipped, so re-uploading is safe.
    - Accounts created by an import are not primary: use their `id` as `account_id` in the forecast.
    """
    raw = await file.read(STATEMENT_MAX_BYTES + 1)

    try:
        imported, duplicates = await statement_manager.import_bank_statement(db, file.filename, raw, account_id)
    except (StatementImportError, StatementParseError) as exc:
        logger.warning(STATEMENT_IMPORT_REJECTED_LOG, exc)
        raise bad_request(str(exc))
    except StatementAccountNotFoundError:
        raise not_found(ACCOUNT_NOT_FOUND)

    return {
        "status": IMPORT_STATUS_SUCCESS,
        "transactions_imported": imported,
        "duplicates_skipped": duplicates,
    }
