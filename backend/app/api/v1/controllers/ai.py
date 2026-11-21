from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.errors import model_unavailable
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_AI
from app.const.llm import UNKNOWN_MODEL_NAME
from app.core.config import settings
from app.models.user import User
from app.schemas.action import DirectExplainRequest, ExplainActionResponse
from app.const.cards import RESPONSE_SOURCE_GUARDRAIL
from app.const.guardrails import GUARDRAIL_MODEL_NAME
from app.services.guardrails import GuardrailBlockedError
from app.services.llm import LLMUnavailableError, advise, check_model_health, explain_action

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

    Guardrails: illegal requests and prompt injection are refused (`response_source` = `guardrail`).
    """
    try:
        answer = await explain_action(facts=payload.facts, question=payload.question)
    except GuardrailBlockedError as blocked:
        return _refusal(payload, blocked)
    except LLMUnavailableError as exc:
        raise model_unavailable(exc)

    return _model_answer(payload, answer)


@ai_router.post(
    "/advisor",
    response_model=ExplainActionResponse,
    summary="Advisor chat with the LLM",
    responses={503: {"description": "The model endpoint does not respond"}},
)
async def advisor_chat(payload: DirectExplainRequest, current_user: User = Depends(get_current_user)):
    """
    The Advisor page chat: forecast facts and the owner's notes in `facts`, earlier turns in `history`.
    The system prompt lives on the server, so the browser cannot replace it.

    Guardrails: illegal requests and prompt injection are refused (`response_source` = `guardrail`).
    """
    try:
        answer = await advise(facts=payload.facts, question=payload.question, history=payload.history)
    except GuardrailBlockedError as blocked:
        return _refusal(payload, blocked)
    except LLMUnavailableError as exc:
        raise model_unavailable(exc)

    return _model_answer(payload, answer)


def _model_answer(payload: DirectExplainRequest, answer: str) -> ExplainActionResponse:
    return ExplainActionResponse(
        model=settings.MODEL_NAME or UNKNOWN_MODEL_NAME,
        question=payload.question,
        answer=answer,
        facts_used=payload.facts,
    )


def _refusal(payload: DirectExplainRequest, blocked: GuardrailBlockedError) -> ExplainActionResponse:
    return ExplainActionResponse(
        model=GUARDRAIL_MODEL_NAME,
        question=payload.question,
        answer=blocked.refusal,
        facts_used={},
        response_source=RESPONSE_SOURCE_GUARDRAIL,
    )
