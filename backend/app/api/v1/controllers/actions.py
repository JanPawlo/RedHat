from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import conflict, not_found
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_ACTIONS
from app.const.messages import AGENT_ACTION_NOT_FOUND
from app.managers import action_manager, card_manager
from app.managers.action_manager import InvalidStatusTransitionError
from app.models.user import User
from app.schemas.action import (
    AgentActionResponse,
    AgentActionUpdate,
    ExplainActionRequest,
    ExplainActionResponse,
)

actions_router = APIRouter(prefix="/actions", tags=[TAG_ACTIONS], responses=RESPONSE_UNAUTHORIZED)


@actions_router.get("", response_model=List[AgentActionResponse], summary="List decision cards")
async def list_agent_actions(
    status: Optional[str] = Query(None, description="pending, simulated, approved, rejected or executed"),
    agent_type: Optional[str] = Query(None, description="e.g. payables_optimizer, fraud_guard"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    Cards the agents created (newest first). The swipe deck shows `pending` cards.
    Cards come from the seed and from invoice validation (`auto_create_card=true`).
    """
    return await action_manager.list_actions(db, status, agent_type)


@actions_router.post(
    "/{action_id}/update-status",
    response_model=AgentActionResponse,
    summary="Swipe: approve, reject, simulate or undo a card",
    responses={404: {"description": "Card not found"}, 409: {"description": "This status change is not allowed"}},
)
async def update_action_status(
    action_id: UUID,
    payload: AgentActionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    Allowed status changes:

    - `pending` → `simulated` / `approved` / `rejected`
    - `simulated` → `approved` / `rejected`
    - `approved` → `executed` / `rejected` / `pending` (undo)
    - `rejected` → `pending` (undo)
    - `executed` is final

    Anything else returns 409. `user_feedback` can be sent alone or together with the status.
    """
    try:
        action = await action_manager.update_action_status(db, action_id, payload)
    except InvalidStatusTransitionError as exc:
        raise conflict(str(exc))

    if not action:
        raise not_found(AGENT_ACTION_NOT_FOUND)

    return action


@actions_router.post(
    "/{action_id}/explain",
    response_model=ExplainActionResponse,
    summary="Ask why: the LLM explains a card from the engine's numbers",
    responses={404: {"description": "Card not found"}},
)
async def explain_agent_action(
    action_id: UUID,
    payload: Optional[ExplainActionRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    Separate from the card's front text: the model gets the forecast engine's facts for this card (lowest balance
    with and without it, the revenue scenarios behind the confidence, the biggest outflows, recurring payments)
    and explains them. `facts_used` shows exactly what it got. When the model does not respond,
    `response_source` is `deterministic_fallback` and the answer is built from the same facts without AI.
    """
    request = payload or ExplainActionRequest()
    explanation = await card_manager.explain_card(db, action_id, request.question, [turn.model_dump() for turn in request.history])

    if not explanation:
        raise not_found(AGENT_ACTION_NOT_FOUND)

    return explanation
