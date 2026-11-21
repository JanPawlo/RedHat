import json
from typing import Any, Dict, List

import httpx

from app.const.llm import (
    ADVISOR_MAX_TOKENS,
    ADVISOR_PROMPT,
    CHAT_TEMPLATE_KWARGS,
    COMPLETION_MAX_TOKENS,
    COMPLETION_TEMPERATURE,
    COMPLETION_TIMEOUT_SECONDS,
    HEALTH_TIMEOUT_SECONDS,
    MODEL_STATUS_CONNECTED,
    RAIL_ADVISOR,
    RAIL_EXPLAIN,
    SYSTEM_PROMPT,
)
from app.const.messages import MODEL_UNEXPECTED_RESPONSE
from app.core.config import settings
from app.services.guardrails import check_answer, check_request, clean_history, sanitize_facts


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


async def explain_action(facts: Dict[str, Any], question: str) -> str:
    """
    Ask the RHOAI open-weights LLM to explain pre-calculated financial facts.
    Raises `GuardrailBlockedError` (with the refusal text) when the question is not allowed.
    """
    check_request([question], RAIL_EXPLAIN)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _facts_message(facts, question)},
    ]
    return await _guarded_completion(messages, COMPLETION_MAX_TOKENS)


async def advise(facts: Dict[str, Any], question: str, history: List[Dict[str, str]]) -> str:
    """
    General advisor chat: engine facts plus the owner's notes, with earlier turns as context.
    Raises `GuardrailBlockedError` when the question is not allowed; refused earlier exchanges are dropped from the history.
    """
    check_request([question], RAIL_ADVISOR)

    messages = [
        {"role": "system", "content": ADVISOR_PROMPT},
        *clean_history(history),
        {"role": "user", "content": _facts_message(facts, question)},
    ]
    return await _guarded_completion(messages, ADVISOR_MAX_TOKENS)


def _facts_message(facts: Dict[str, Any], question: str) -> str:
    safe_facts = sanitize_facts(facts)
    return f"FACTS:\n{json.dumps(safe_facts, default=str)}\n\nQUESTION:\n{question}"


async def _guarded_completion(messages: List[Dict[str, str]], max_tokens: int) -> str:
    payload = {
        "model": settings.MODEL_NAME,
        "temperature": COMPLETION_TEMPERATURE,
        "max_tokens": max_tokens,
        "chat_template_kwargs": CHAT_TEMPLATE_KWARGS,
        "messages": messages,
    }

    data = await _post_json("chat/completions", payload, COMPLETION_TIMEOUT_SECONDS)
    answer = _extract_answer(data)

    return check_answer(answer)
