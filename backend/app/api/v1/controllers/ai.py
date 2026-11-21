from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import model_unavailable
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_AI
from app.const.llm import UNKNOWN_MODEL_NAME
from app.core.config import settings
from app.models.user import User
from app.managers import agent_engine_log_manager
from app.schemas.action import DirectExplainRequest, ExplainActionResponse
from app.schemas.agent_engine_log import AgentCapabilityRequestResponse, AgentEngineCallLogResponse
from app.services.llm import LLMUnavailableError, check_model_health, explain_action_with_engine

ai_router = APIRouter(prefix="/ai", tags=[TAG_AI], responses=RESPONSE_UNAUTHORIZED)
LOG_LIMIT_MAX = 200


@ai_router.get("/engine-calls", response_model=List[AgentEngineCallLogResponse], summary="List model-requested engine calls")
async def list_engine_calls(
    action_id: Optional[UUID] = Query(None),
    request_id: Optional[UUID] = Query(None),
    limit: int = Query(50, ge=1, le=LOG_LIMIT_MAX),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """Newest first; each row shows the requested tool, validated input, result, status and elapsed time."""
    return await agent_engine_log_manager.list_engine_calls(
        db, action_id=action_id, request_id=request_id, limit=limit, offset=offset
    )


@ai_router.get(
    "/capability-requests",
    response_model=List[AgentCapabilityRequestResponse],
    summary="List model-reported engine capability gaps",
)
async def list_capability_requests(
    action_id: Optional[UUID] = Query(None),
    request_id: Optional[UUID] = Query(None),
    limit: int = Query(50, ge=1, le=LOG_LIMIT_MAX),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """These are AI-reported needs for review, not verified engine defects."""
    return await agent_engine_log_manager.list_capability_requests(
        db, action_id=action_id, request_id=request_id, limit=limit, offset=offset
    )


@ai_router.get(
    "/health",
    summary="Is the AI model reachable",
    responses={503: {"description": "The model endpoint does not respond"}},
)
async def ai_model_health(current_user: User = Depends(get_current_user)):
    """
    Asks the vLLM endpoint on OpenShift AI for its models. Returns the configured model and the ones available.
    Source of the "OpenShift AI · vLLM · model active" badge in the header.
    """
    try:
        return await check_model_health()
    except LLMUnavailableError as exc:
        raise model_unavailable(exc)


@ai_router.post(
    "/explain",
    response_model=ExplainActionResponse,
    summary="Explain arbitrary facts with the LLM",
    responses={503: {"description": "The model endpoint does not respond"}},
)
async def explain_card_facts(
    payload: DirectExplainRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    Sends client-supplied facts and a question to the model. The model may request additional forecast or
    simulation results through backend engine tools; database access and calculations stay in the backend.
    """
    try:
        answer, engine_calls, request_id = await explain_action_with_engine(
            db=db,
            facts=payload.facts,
            question=payload.question,
            user_id=current_user.id,
        )
    except LLMUnavailableError as exc:
        raise model_unavailable(exc)

    return ExplainActionResponse(
        model=settings.MODEL_NAME or UNKNOWN_MODEL_NAME,
        request_id=request_id,
        question=payload.question,
        answer=answer,
        facts_used={**payload.facts, **({"engine_tool_calls": engine_calls} if engine_calls else {})},
    )
