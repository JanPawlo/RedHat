import json
from typing import Any, Dict
import httpx
from app.core.config import settings

SYSTEM_PROMPT = (
    "You are an Autonomous CFO assistant for small and medium-sized business owners. "
    "Explain financial recommendations in simple, friendly, plain language without corporate jargon. "
    "STRICT RULE: Never invent or calculate any numbers yourself. Use ONLY the exact numbers provided in FACTS. "
    "Keep your explanation concise (2-4 short sentences)."
)


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
    """Ask the RHOAI open-weights LLM to explain pre-calculated financial facts."""
    url = f"{settings.MODEL_ENDPOINT_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.MODEL_NAME,
        "temperature": 0.2,
        "max_tokens": 180,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"FACTS:\n{json.dumps(facts, default=str)}\n\nQUESTION:\n{question}",
            },
        ],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=_headers())
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
