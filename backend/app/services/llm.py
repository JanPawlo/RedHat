import json
import re
from typing import Any, Dict, Sequence

import httpx

from app.const.llm import (
    CHAT_TEMPLATE_KWARGS,
    COMPLETION_MAX_TOKENS,
    COMPLETION_TEMPERATURE,
    COMPLETION_TIMEOUT_SECONDS,
    HEALTH_TIMEOUT_SECONDS,
    MODEL_STATUS_CONNECTED,
    SYSTEM_PROMPT,
)
from app.const.messages import MODEL_UNEXPECTED_RESPONSE
from app.core.config import settings


THINK_BLOCK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)


class LLMUnavailableError(Exception):
    pass


def _url(path: str) -> str:
    return f"{settings.MODEL_ENDPOINT_URL.rstrip('/')}/{path}"


def _headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.MODEL_API_KEY:
        headers["Authorization"] = f"Bearer {settings.MODEL_API_KEY}"
    return headers


async def _get_json(path: str, timeout: float) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(_url(path), headers=_headers())
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LLMUnavailableError(str(exc)) from exc


async def _post_json(path: str, payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(_url(path), json=payload, headers=_headers())
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LLMUnavailableError(str(exc)) from exc


def _extract_answer(data: Dict[str, Any]) -> str:
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise LLMUnavailableError(MODEL_UNEXPECTED_RESPONSE) from exc


async def check_model_health() -> Dict[str, Any]:
    """Check connectivity to the OpenShift AI (RHOAI / vLLM) model endpoint."""
    data = await _get_json("models", HEALTH_TIMEOUT_SECONDS)
    if not isinstance(data, dict):
        raise LLMUnavailableError(MODEL_UNEXPECTED_RESPONSE)

    models = [model.get("id") for model in data.get("data", []) if isinstance(model, dict)]
    return {
        "status": MODEL_STATUS_CONNECTED,
        "configured_model": settings.MODEL_NAME,
        "available_models": models,
    }


def _strip_thinking(text: str) -> str:
    return THINK_BLOCK.sub("", text).replace("<think>", "").replace("</think>", "").strip()


async def explain_action(
    facts: Dict[str, Any],
    question: str,
    history: Sequence[Dict[str, str]] = (),
    system_prompt: str = SYSTEM_PROMPT,
    max_tokens: int = COMPLETION_MAX_TOKENS,
) -> str:
    """Ask the RHOAI open-weights LLM to explain pre-calculated financial facts; `history` = earlier chat turns."""
    payload = {
        "model": settings.MODEL_NAME,
        "temperature": COMPLETION_TEMPERATURE,
        "max_tokens": max_tokens,
        "chat_template_kwargs": CHAT_TEMPLATE_KWARGS,
        "messages": [
            {"role": "system", "content": system_prompt},
            *history,
            {
                "role": "user",
                "content": f"FACTS:\n{json.dumps(facts, default=str)}\n\nQUESTION:\n{question}",
            },
        ],
    }

    data = await _post_json("chat/completions", payload, COMPLETION_TIMEOUT_SECONDS)
    answer = _strip_thinking(_extract_answer(data))
    if not answer:
        raise LLMUnavailableError(MODEL_UNEXPECTED_RESPONSE)
    return answer
