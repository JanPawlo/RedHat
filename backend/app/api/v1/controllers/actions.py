from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import conflict, model_unavailable, not_found
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

actions_router = APIRouter(prefix="/actions", tags=["Agent Actions"])


@actions_router.get("", response_model=List[AgentActionResponse])
async def list_agent_actions(
    status: Optional[str] = None,
    agent_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    return await action_manager.list_actions(db, status, agent_type)


@actions_router.post("/{action_id}/update-status", response_model=AgentActionResponse)
async def update_action_status(
    action_id: UUID,
    payload: AgentActionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    try:
        action = await action_manager.update_action_status(db, action_id, payload)
    except InvalidStatusTransitionError as exc:
        raise conflict(str(exc))

    if not action:
        raise not_found(AGENT_ACTION_NOT_FOUND)

    return action


@actions_router.post("/{action_id}/explain", response_model=ExplainActionResponse)
async def explain_agent_action(
    action_id: UUID,
    payload: Optional[ExplainActionRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    try:
        explanation = await action_manager.explain_agent_action(db, action_id, payload)
    except LLMUnavailableError as exc:
        raise model_unavailable(exc)

    if not explanation:
        raise not_found(AGENT_ACTION_NOT_FOUND)

    return explanation
