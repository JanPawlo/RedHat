from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import conflict, not_found
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_BANK_CONNECTIONS
from app.const.messages import BANK_ALREADY_CONNECTED, BANK_NOT_CONNECTED, BANK_NOT_FOUND
from app.managers import bank_manager
from app.managers.bank_manager import BankAlreadyConnectedError, BankNotConnectedError, BankNotFoundError
from app.models.user import User

bank_connections_router = APIRouter(prefix="/bank-connections", tags=[TAG_BANK_CONNECTIONS], responses=RESPONSE_UNAUTHORIZED)

RESPONSE_UNKNOWN_BANK = {404: {"description": "Unknown bank"}}


@bank_connections_router.get("", summary="Banks available for connection and their status")
async def list_bank_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
) -> List[Dict[str, Any]]:
    """
    Mock PSD2 catalogue: every bank with `status` `available` or `connected`. Connected banks list
    their accounts with today's balance and the number of imported transactions.
    """
    return await bank_manager.list_bank_connections(db)


@bank_connections_router.post(
    "/{bank_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Connect a bank (simulated consent)",
    responses={**RESPONSE_UNKNOWN_BANK, 409: {"description": "Bank already connected"}},
)
async def connect_bank(
    bank_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
) -> Dict[str, Any]:
    """
    Simulates the PSD2 consent (valid 90 days), creates the bank's accounts (not primary, so the forecast
    of the main account does not change) and imports the last 60 days of transactions.
    """
    try:
        return await bank_manager.connect_bank(db, bank_id)
    except BankNotFoundError:
        raise not_found(BANK_NOT_FOUND)
    except BankAlreadyConnectedError:
        raise conflict(BANK_ALREADY_CONNECTED)


@bank_connections_router.post(
    "/{bank_id}/sync",
    summary="Sync a connected bank",
    responses={**RESPONSE_UNKNOWN_BANK, 409: {"description": "Bank not connected"}},
)
async def sync_bank(
    bank_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
) -> Dict[str, Any]:
    """Fetches transactions again; only new ones are stored (`imported`), known ones are `skipped`. Balance comes from the bank."""
    try:
        return await bank_manager.sync_bank(db, bank_id)
    except BankNotFoundError:
        raise not_found(BANK_NOT_FOUND)
    except BankNotConnectedError:
        raise conflict(BANK_NOT_CONNECTED)


@bank_connections_router.delete(
    "/{bank_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect a bank",
    responses={**RESPONSE_UNKNOWN_BANK, 409: {"description": "Bank not connected"}},
)
async def disconnect_bank(
    bank_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
) -> Response:
    """Withdraws the consent and removes the bank's accounts with their transactions."""
    try:
        await bank_manager.disconnect_bank(db, bank_id)
    except BankNotFoundError:
        raise not_found(BANK_NOT_FOUND)
    except BankNotConnectedError:
        raise conflict(BANK_NOT_CONNECTED)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
