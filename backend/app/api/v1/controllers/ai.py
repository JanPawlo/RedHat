from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.errors import model_unavailable
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_AI
from app.const.llm import (
    ADVISOR_MAX_TOKENS,
    ADVISOR_PROMPT,
    COMPLETION_MAX_TOKENS,
    EXPLAIN_MODE_ADVISOR,
    SYSTEM_PROMPT,
    UNKNOWN_MODEL_NAME,
)
from app.core.config import settings
from app.models.user import User
from app.schemas.action import DirectExplainRequest, ExplainActionResponse
from app.services.llm import LLMUnavailableError, check_model_health, explain_action

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
async def explain_card_facts(payload: DirectExplainRequest, current_user: User = Depends(get_current_user)):
    """
    Sends client-supplied facts and a question to the model. Prefer `POST /actions/{id}/explain`
    for stored cards: there the facts come from the forecast engine, not from the client.

    `mode="advisor"` uses the CFO advisor prompt (longer answers, the owner's notes in FACTS) and
    `history` carries earlier turns of the chat (oldest first) so follow-up questions keep their context.
    The system prompt always stays on the server.
    """
    advisor = payload.mode == EXPLAIN_MODE_ADVISOR
    try:
        answer = await explain_action(
            facts=payload.facts,
            question=payload.question,
            history=[turn.model_dump() for turn in payload.history],
            system_prompt=ADVISOR_PROMPT if advisor else SYSTEM_PROMPT,
            max_tokens=ADVISOR_MAX_TOKENS if advisor else COMPLETION_MAX_TOKENS,
        )
    except LLMUnavailableError as exc:
        raise model_unavailable(exc)

    return ExplainActionResponse(
        model=settings.MODEL_NAME or UNKNOWN_MODEL_NAME,
        question=payload.question,
        answer=answer,
        facts_used=payload.facts,
    )
