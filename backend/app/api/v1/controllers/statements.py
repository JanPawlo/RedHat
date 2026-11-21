import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import bad_request, not_found
from app.const.messages import ACCOUNT_NOT_FOUND, STATEMENT_IMPORT_REJECTED_LOG
from app.const.statement import IMPORT_STATUS_SUCCESS, STATEMENT_MAX_BYTES
from app.managers import statement_manager
from app.managers.statement_manager import StatementAccountNotFoundError, StatementImportError
from app.models.user import User
from app.services.statement_parser import StatementParseError

logger = logging.getLogger(__name__)

statements_router = APIRouter(prefix="/statements", tags=["Statements"])


@statements_router.post("/upload/csv")
async def upload_bank_statement(
    file: UploadFile = File(...),
    account_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
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
