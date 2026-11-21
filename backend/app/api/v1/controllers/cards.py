from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_ACTIONS
from app.managers import card_manager
from app.models.user import User

cards_router = APIRouter(prefix="/cards", tags=[TAG_ACTIONS], responses=RESPONSE_UNAUTHORIZED)


@cards_router.get("", summary="Pending decision cards in the frontend format, with the engine's effect")
async def list_cards(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
) -> List[Dict[str, Any]]:
    """
    Each pending card is previewed by the forecast engine: `confidence` (share of revenue scenarios that keep the
    buffer if approved), `recommendation` (right when the card raises the lowest balance, does not lower confidence and
    keeps the buffer), the 8-week bars before/after and the facts on the back. Swipe with
    `POST /actions/{id}/update-status`; "Ask why" with `POST /actions/{id}/explain`.
    """
    return await card_manager.list_ui_cards(db)


@cards_router.post("/generate", summary="Let the agents create cards from the current forecast")
async def generate_cards(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
) -> Dict[str, Any]:
    """
    Creates cards for what the engine finds: liquidity gap (credit line), early-payment discounts, supplier invoices
    falling into the gap (ask to move), customers who usually pay late (offer a discount), free cash (deposit).
    Cards that already exist (same dedupe key) are not created again.
    """
    return await card_manager.generate_cards(db)
