from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.api.errors import model_unavailable
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_AI
from app.const.llm import UNKNOWN_MODEL_NAME
from app.core.config import settings
from app.models.user import User
from app.schemas.action import DirectExplainRequest, ExplainActionResponse
from app.services.llm import LLMUnavailableError, check_model_health, explain_action_with_engine

ai_router = APIRouter(prefix="/ai", tags=[TAG_AI], responses=RESPONSE_UNAUTHORIZED)


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
        answer, engine_calls = await explain_action_with_engine(
            db=db,
            facts=payload.facts,
            question=payload.question,
        )
    except LLMUnavailableError as exc:
        raise model_unavailable(exc)

    return ExplainActionResponse(
        model=settings.MODEL_NAME or UNKNOWN_MODEL_NAME,
        question=payload.question,
        answer=answer,
        facts_used={**payload.facts, **({"engine_tool_calls": engine_calls} if engine_calls else {})},
    )
