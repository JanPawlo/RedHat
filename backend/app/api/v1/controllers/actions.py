from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import conflict, not_found, too_many_requests
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_ACTIONS
from app.const.messages import AGENT_ACTION_NOT_FOUND
from app.managers import action_manager, card_manager
from app.managers.action_manager import InvalidStatusTransitionError
from app.models.user import User
from app.services.llm_limiter import RateLimitedError
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
    Cards come from the seed and deterministic card generation.
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
    responses={404: {"description": "Card not found"}, 429: {"description": "The user already has a question in progress or asked too many in a minute"}},
)
async def explain_agent_action(
    action_id: UUID,
    payload: Optional[ExplainActionRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    Separate from the card's front text: the model gets the forecast engine's facts for this card (lowest balance
    with and without it, the revenue scenarios behind the confidence, the biggest outflows, recurring payments).
    The default "why" question is answered from the card's stored, already checked explanation. Other questions
    carry `history` (earlier turns) and may use a what-if simulation through bounded engine tools; the backend
    loads database data and executes calculations. `facts_used.engine_tool_calls` reports those requests and results;
    persistent traces are available from `GET /ai/engine-calls` and model-reported gaps from
    `GET /ai/capability-requests`. Answers pass the card guardrails (numbers must come from the facts or the tools).
    When the model does not respond,
    `response_source` is `deterministic_fallback` and the answer is built from the same facts without AI.
    """
    request = payload or ExplainActionRequest()
    user_key = str(current_user.id)

    try:
        explanation = await card_manager.explain_card(
            db,
            action_id,
            request.question,
            history=[turn.model_dump() for turn in request.history],
            user_id=current_user.id,
            user_key=user_key,
        )
    except RateLimitedError as limited:
        raise too_many_requests(user_key, limited.message, limited.retry_after)

    if not explanation:
        raise not_found(AGENT_ACTION_NOT_FOUND)

    return explanation
