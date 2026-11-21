from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.const.action import ACTION_STATUS_TRANSITIONS
from app.const.cards import RESPONSE_SOURCE_GUARDRAIL, RESPONSE_SOURCE_MODEL
from app.const.llm import UNKNOWN_MODEL_NAME
from app.const.messages import INVALID_STATUS_TRANSITION
from app.core.config import settings
from app.models.action import AgentAction
from app.schemas.action import AgentActionUpdate, ExplainActionRequest, ExplainActionResponse
from app.const.guardrails import GUARDRAIL_MODEL_NAME
from app.services.guardrails import GuardrailBlockedError
from app.services.llm import explain_action


class InvalidStatusTransitionError(Exception):
    pass


async def list_actions(db: AsyncSession, status: Optional[str], agent_type: Optional[str]) -> List[AgentAction]:
    query = select(AgentAction).order_by(desc(AgentAction.created_at))

    if status:
        query = query.where(AgentAction.status == status)
    if agent_type:
        query = query.where(AgentAction.agent_type == agent_type)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_action(db: AsyncSession, action_id: UUID) -> Optional[AgentAction]:
    result = await db.execute(select(AgentAction).where(AgentAction.id == action_id))
    return result.scalar_one_or_none()


def _ensure_status_transition(current: str, target: str) -> None:
    if target == current:
        return

    if target not in ACTION_STATUS_TRANSITIONS.get(current, ()):
        raise InvalidStatusTransitionError(INVALID_STATUS_TRANSITION.format(current=current, target=target))


async def update_action_status(db: AsyncSession, action_id: UUID, payload: AgentActionUpdate) -> Optional[AgentAction]:
    action = await get_action(db, action_id)
    if not action:
        return None

    changes = payload.model_dump(exclude_unset=True)
    if changes.get("status"):
        _ensure_status_transition(action.status, changes["status"])

    for field, value in changes.items():
        if value is not None or field == "user_feedback":
            setattr(action, field, value)

    await db.flush()
    await db.refresh(action)
    return action


def _build_action_facts(action: AgentAction) -> Dict[str, Any]:
    return {
        "title": action.title,
        "agent_type": action.agent_type,
        "trigger_reason": action.trigger_reason,
        "recommended_action": action.recommended_action,
        "target_amount": float(action.target_amount) if action.target_amount is not None else None,
        "currency": action.currency,
        "impact_simulation": action.impact_simulation,
        "status": action.status,
        "execution_mode": action.execution_mode,
    }


async def explain_agent_action(
    db: AsyncSession,
    action_id: UUID,
    payload: Optional[ExplainActionRequest],
) -> Optional[ExplainActionResponse]:
    action = await get_action(db, action_id)
    if not action:
        return None

    request = payload or ExplainActionRequest()
    facts = _build_action_facts(action)

    try:
        answer = await explain_action(facts=facts, question=request.question)
        model, source = settings.MODEL_NAME or UNKNOWN_MODEL_NAME, RESPONSE_SOURCE_MODEL
    except GuardrailBlockedError as blocked:
        answer, model, source = blocked.refusal, GUARDRAIL_MODEL_NAME, RESPONSE_SOURCE_GUARDRAIL

    return ExplainActionResponse(
        action_id=action.id,
        model=model,
        question=request.question,
        answer=answer,
        facts_used=facts,
        response_source=source,
    )
