from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.errors import model_unavailable
from app.const.llm import UNKNOWN_MODEL_NAME
from app.core.config import settings
from app.models.user import User
from app.schemas.action import DirectExplainRequest, ExplainActionResponse
from app.services.llm import LLMUnavailableError, check_model_health, explain_action

ai_router = APIRouter(prefix="/ai", tags=["AI Model"])


@ai_router.get("/health")
async def ai_model_health(current_user: User = Depends(get_current_user)):
    try:
        return await check_model_health()
    except LLMUnavailableError as exc:
        raise model_unavailable(exc)


@ai_router.post("/explain", response_model=ExplainActionResponse)
async def explain_card_facts(payload: DirectExplainRequest, current_user: User = Depends(get_current_user)):
    try:
        answer = await explain_action(facts=payload.facts, question=payload.question)
    except LLMUnavailableError as exc:
        raise model_unavailable(exc)

    return ExplainActionResponse(
        model=settings.MODEL_NAME or UNKNOWN_MODEL_NAME,
        question=payload.question,
        answer=answer,
        facts_used=payload.facts,
    )
