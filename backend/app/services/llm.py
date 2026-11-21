import json
import logging
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

import httpx

from app.const.engine_tools import ENGINE_TOOLS, ENGINE_TOOLS_PROMPT, TOOL_MAX_ROUNDS
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


# A tool call the model asked for: (tool name, raw JSON arguments) → result shown to the model.
ToolRunner = Callable[[str, Any], Awaitable[Dict[str, Any]]]

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
    run_tool: Optional[ToolRunner] = None,
) -> str:
    """
    Ask the RHOAI open-weights LLM to explain pre-calculated financial facts; `history` = earlier chat turns.
    With `run_tool` the model may ask the engine for a forecast or a what-if (`ENGINE_TOOLS`) before answering.
    Guardrails: raises `GuardrailBlockedError` (with the refusal text) when the question is not allowed; facts are
    cleaned of instruction-like text; refused earlier exchanges are dropped; the answer is checked and identifiers masked.
    """
    check_request([question], rail)

    messages = [
        {"role": "system", "content": system_prompt + (ENGINE_TOOLS_PROMPT if run_tool else "")},
        *clean_history(list(history)),
        {"role": "user", "content": _facts_message(facts, question)},
    ]
    if run_tool:
        answer = await chat_with_tools(messages, ENGINE_TOOLS, run_tool, max_tokens, COMPLETION_TEMPERATURE)
    else:
        answer = await chat(messages, max_tokens, COMPLETION_TEMPERATURE)
    if not answer:
        raise LLMUnavailableError(MODEL_UNEXPECTED_RESPONSE)
    return check_answer(answer)


async def advise(
    facts: Dict[str, Any], question: str, history: Sequence[Dict[str, str]], run_tool: Optional[ToolRunner] = None
) -> str:
    """General advisor chat: engine facts plus the owner's notes, with earlier turns as context (same guardrails)."""
    return await explain_action(facts, question, history, ADVISOR_PROMPT, ADVISOR_MAX_TOKENS, RAIL_ADVISOR, run_tool)


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

    payload = _payload(messages, max_tokens, temperature)
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


async def chat_with_tools(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    run_tool: ToolRunner,
    max_tokens: int,
    temperature: float,
) -> str:
    """
    A chat completion where the model may call `tools` first. At most `TOOL_MAX_ROUNDS` rounds of calls, each
    executed by `run_tool`; then one last completion with tools off, so the loop always ends with text.
    A model that answers straight away costs one call, the same as `chat`.
    """
    messages = list(messages)
    for _ in range(TOOL_MAX_ROUNDS):
        payload = _payload(messages, max_tokens, temperature)
        payload["tools"], payload["tool_choice"] = tools, "auto"
        message = _assistant_message(await _post_json("chat/completions", payload, COMPLETION_TIMEOUT_SECONDS))
        tool_calls = [call for call in message.get("tool_calls") or [] if isinstance(call, dict)]
        if not tool_calls:
            return _strip_thinking(message.get("content") or "")

        messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": tool_calls})
        for call in tool_calls:
            function = call.get("function") or {}
            name = function.get("name", "")
            result = await run_tool(name, function.get("arguments", "{}"))
            messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "name": name, "content": json.dumps(result, default=str, ensure_ascii=False)})

    data = await _post_json("chat/completions", _payload(messages, max_tokens, temperature), COMPLETION_TIMEOUT_SECONDS)
    return _strip_thinking(_extract_answer(data))


def _payload(messages: List[Dict[str, Any]], max_tokens: int, temperature: float) -> Dict[str, Any]:
    return {
        "model": settings.MODEL_NAME,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "chat_template_kwargs": CHAT_TEMPLATE_KWARGS,
        "messages": messages,
    }


def _assistant_message(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMUnavailableError(MODEL_UNEXPECTED_RESPONSE) from exc
    if not isinstance(message, dict):
        raise LLMUnavailableError(MODEL_UNEXPECTED_RESPONSE)
    return message
