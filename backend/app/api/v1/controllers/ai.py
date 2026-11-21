from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.errors import model_unavailable
from app.models.user import User
from app.services.llm import LLMUnavailableError, check_model_health

ai_router = APIRouter(prefix="/ai", tags=["AI Model"])


@ai_router.get("/health")
async def ai_model_health(current_user: User = Depends(get_current_user)):
    try:
        return await check_model_health()
    except LLMUnavailableError as exc:
        raise model_unavailable(exc)
