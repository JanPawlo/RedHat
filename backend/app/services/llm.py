import json
import logging
import re
from typing import Any, Dict, List, Optional, Sequence

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


THINK_BLOCK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)

logger = logging.getLogger(__name__)

# vLLM supports `response_format` with a JSON schema; if a server rejects it we stop sending it.
_structured_output_supported = True


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
    rail: str = RAIL_EXPLAIN,
) -> str:
    """
    Ask the RHOAI open-weights LLM to explain pre-calculated financial facts; `history` = earlier chat turns.
    Guardrails: raises `GuardrailBlockedError` (with the refusal text) when the question is not allowed; facts are
    cleaned of instruction-like text; refused earlier exchanges are dropped; the answer is checked and identifiers masked.
    """
    check_request([question], rail)

    messages = [
        {"role": "system", "content": system_prompt},
        *clean_history(list(history)),
        {"role": "user", "content": _facts_message(facts, question)},
    ]
    payload = {
        "model": settings.MODEL_NAME,
        "temperature": COMPLETION_TEMPERATURE,
        "max_tokens": max_tokens,
        "chat_template_kwargs": CHAT_TEMPLATE_KWARGS,
        "messages": messages,
    }

    data = await _post_json("chat/completions", payload, COMPLETION_TIMEOUT_SECONDS)
    answer = _strip_thinking(_extract_answer(data))
    if not answer:
        raise LLMUnavailableError(MODEL_UNEXPECTED_RESPONSE)
    return check_answer(answer)


async def advise(facts: Dict[str, Any], question: str, history: Sequence[Dict[str, str]]) -> str:
    """General advisor chat: engine facts plus the owner's notes, with earlier turns as context (same guardrails)."""
    return await explain_action(facts, question, history, ADVISOR_PROMPT, ADVISOR_MAX_TOKENS, RAIL_ADVISOR)


def _facts_message(facts: Dict[str, Any], question: str) -> str:
    safe_facts = sanitize_facts(facts)
    return f"FACTS:\n{json.dumps(safe_facts, default=str)}\n\nQUESTION:\n{question}"


async def chat(
    messages: List[Dict[str, str]],
    max_tokens: int,
    temperature: float,
    json_schema: Optional[Dict[str, Any]] = None,
    timeout: float = COMPLETION_TIMEOUT_SECONDS,
) -> str:
    """One chat completion on the RHOAI model; with `json_schema` the server constrains the output to that schema."""
    global _structured_output_supported

    payload: Dict[str, Any] = {
        "model": settings.MODEL_NAME,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "chat_template_kwargs": CHAT_TEMPLATE_KWARGS,
        "messages": messages,
    }
    if json_schema and _structured_output_supported:
        payload["response_format"] = {"type": "json_schema", "json_schema": {"name": "answer", "schema": json_schema}}

    try:
        data = await _post_json("chat/completions", payload, timeout)
    except LLMUnavailableError as exc:
        if "response_format" not in payload or "400" not in str(exc):
            raise
        logger.warning("Model server rejected structured output; continuing without it")
        _structured_output_supported = False
        payload.pop("response_format")
        data = await _post_json("chat/completions", payload, timeout)

    return _strip_thinking(_extract_answer(data))
