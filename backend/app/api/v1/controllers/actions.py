from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import conflict, model_unavailable, not_found
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_ACTIONS
from app.const.messages import AGENT_ACTION_NOT_FOUND
from app.managers import action_manager
from app.managers.action_manager import InvalidStatusTransitionError
from app.models.user import User
from app.schemas.action import (
    AgentActionResponse,
    AgentActionUpdate,
    ExplainActionRequest,
    ExplainActionResponse,
)
from app.services.llm import LLMUnavailableError

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
    summary="Ask why: the LLM explains a card",
    responses={404: {"description": "Card not found"}, 503: {"description": "The AI model does not respond"}},
)
async def explain_agent_action(
    action_id: UUID,
    payload: Optional[ExplainActionRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    Sends the card's facts (amounts, reason, simulated impact) and your question to the model on OpenShift AI.
    The model only explains these facts; `facts_used` shows exactly what it got. Without a body a default question is asked.
    """
    try:
        explanation = await action_manager.explain_agent_action(db, action_id, payload)
    except LLMUnavailableError as exc:
        raise model_unavailable(exc)

    if not explanation:
        raise not_found(AGENT_ACTION_NOT_FOUND)

    return explanation
