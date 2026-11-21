from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.errors import model_unavailable
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_AI
from app.models.user import User
from app.services.llm import LLMUnavailableError, check_model_health

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
