from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import model_unavailable
from app.const.cards import RESPONSE_SOURCE_GUARDRAIL
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_AI
from app.const.guardrails import GUARDRAIL_MODEL_NAME
from app.const.llm import (
    ADVISOR_MAX_TOKENS,
    ADVISOR_PROMPT,
    COMPLETION_MAX_TOKENS,
    EXPLAIN_MODE_ADVISOR,
    RAIL_ADVISOR,
    RAIL_EXPLAIN,
    SYSTEM_PROMPT,
    UNKNOWN_MODEL_NAME,
)
from app.core.config import settings
from app.models.user import User
from app.managers import agent_engine_log_manager
from app.schemas.action import DirectExplainRequest, ExplainActionResponse
from app.managers.engine_tool_manager import EngineToolRunner
from app.schemas.agent_engine_log import AgentCapabilityRequestResponse, AgentEngineCallLogResponse
from app.services.guardrails import GuardrailBlockedError
from app.services.llm import LLMUnavailableError, check_model_health, explain_action

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
    Sends client-supplied facts and a question to the model. Prefer `POST /actions/{id}/explain`
    for stored cards: there the facts come from the forecast engine, not from the client.
    The model may request a forecast or a what-if through backend engine tools (`facts_used.engine_tool_calls`,
    traces in `GET /ai/engine-calls`); database access and calculations stay in the backend.

    `mode="advisor"` uses the CFO advisor prompt (longer answers, the owner's notes in FACTS) and
    `history` carries earlier turns of the chat (oldest first) so follow-up questions keep their context.
    The system prompt always stays on the server.

    Guardrails: illegal requests and prompt injection are refused (`response_source` = `guardrail`).
    """
    return await _answer(db, current_user, payload, advisor=payload.mode == EXPLAIN_MODE_ADVISOR)


@ai_router.post(
    "/advisor",
    response_model=ExplainActionResponse,
    summary="Advisor chat with the LLM",
    responses={503: {"description": "The model endpoint does not respond"}},
)
async def advisor_chat(
    payload: DirectExplainRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
):
    """
    The Advisor page chat: same as `POST /ai/explain` with `mode="advisor"`. Forecast facts and the owner's
    notes in `facts`, earlier turns in `history`. Guardrails and engine tools as on `/ai/explain`.
    """
    return await _answer(db, current_user, payload, advisor=True)


async def _answer(db: AsyncSession, user: User, payload: DirectExplainRequest, advisor: bool) -> ExplainActionResponse:
    tools = EngineToolRunner(db, user_id=user.id)
    try:
        answer = await explain_action(
            facts=payload.facts,
            question=payload.question,
            history=[turn.model_dump() for turn in payload.history],
            system_prompt=ADVISOR_PROMPT if advisor else SYSTEM_PROMPT,
            max_tokens=ADVISOR_MAX_TOKENS if advisor else COMPLETION_MAX_TOKENS,
            rail=RAIL_ADVISOR if advisor else RAIL_EXPLAIN,
            run_tool=tools,
        )
    except GuardrailBlockedError as blocked:
        return _refusal(payload, blocked)
    except LLMUnavailableError as exc:
        raise model_unavailable(exc)

    return ExplainActionResponse(
        model=settings.MODEL_NAME or UNKNOWN_MODEL_NAME,
        request_id=tools.request_id,
        question=payload.question,
        answer=answer,
        facts_used={**payload.facts, **({"engine_tool_calls": tools.calls} if tools.calls else {})},
    )


def _refusal(payload: DirectExplainRequest, blocked: GuardrailBlockedError) -> ExplainActionResponse:
    return ExplainActionResponse(
        model=GUARDRAIL_MODEL_NAME,
        question=payload.question,
        answer=blocked.refusal,
        facts_used={},
        response_source=RESPONSE_SOURCE_GUARDRAIL,
    )
