import json
from typing import Any, Dict
import httpx
from app.core.config import settings

SYSTEM_PROMPT = (
    "You are an assistant explaining a financial recommendation to a small-business owner. "
    "The evidence below was assembled by the backend from PostgreSQL and includes deterministic calculations. "
    "Explain what the stored evidence means in plain, friendly language. Do not choose a different action, "
    "recalculate amounts, infer missing data, or invent facts. Use only exact financial values present in the evidence. "
    "If the evidence is missing or insufficient, say so clearly. Keep the answer to 2-4 short sentences."
)


class LLMResponseError(RuntimeError):
    """The configured model returned a response that cannot be used as an explanation."""


def _headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.MODEL_API_KEY:
        headers["Authorization"] = f"Bearer {settings.MODEL_API_KEY}"
    return headers


async def check_model_health() -> Dict[str, Any]:
    """Check connectivity to the OpenShift AI (RHOAI / vLLM) model endpoint."""
    url = f"{settings.MODEL_ENDPOINT_URL.rstrip('/')}/models"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=_headers())
        response.raise_for_status()
        data = response.json()
        models = [m.get("id") for m in data.get("data", [])]
        return {
            "status": "connected",
            "endpoint": settings.MODEL_ENDPOINT_URL,
            "configured_model": settings.MODEL_NAME,
            "available_models": models,
        }


async def explain_action(facts: Dict[str, Any], question: str) -> str:
    """Ask RHOAI to explain PostgreSQL-backed facts; all financial decisions remain deterministic."""
    url = f"{settings.MODEL_ENDPOINT_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.MODEL_NAME,
        "temperature": 0.0,
        "max_tokens": 300,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "AUTHORITATIVE POSTGRESQL EVIDENCE (read-only; do not alter or supplement these facts):\n"
                    f"{json.dumps(facts, default=str, ensure_ascii=False)}\n\n"
                    f"OWNER QUESTION:\n{question}"
                ),
            },
        ],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=_headers())
        response.raise_for_status()
        try:
            data = response.json()
            answer = data["choices"][0]["message"]["content"].strip()
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
            raise LLMResponseError("The model endpoint returned an invalid chat-completion response.") from exc
        if not answer:
            raise LLMResponseError("The model endpoint returned an empty explanation.")
        return answer
