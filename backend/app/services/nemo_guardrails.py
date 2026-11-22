"""
NeMo Guardrails in front of qwen3-8b for the chats people type into (memory/decisions/bonusy.md, "Guardrails").

Our Python guardrails (`services/guardrails.py`) run first; NeMo adds what keywords cannot do:
- input: `self check input`, the model judges whether a reworded question asks for something illegal;
- output: `regex check output`, no personal or banking identifiers leave the model (no GPU call);
- tool calls: `tool call validation` (declared tool, schema-valid arguments) and `regex check tool call`
  (no identifiers in what the agent writes into the engine logs).

This module only builds the request options and reads NeMo's activated-rails log: which rail blocked is taken
from the log (`stop: true`), not guessed from the refusal text.
"""

import logging
from typing import Any, Dict, Optional

from app.const.guardrails import (
    GUARDRAIL_CATEGORY_NEMO,
    GUARDRAIL_LABEL_BACKEND,
    GUARDRAIL_LABEL_NEMO,
    NEMO_BLOCKED_LOG,
    NEMO_CATEGORY,
    NEMO_CATEGORY_PREFIX,
    NEMO_GENERATION_RAIL,
    NEMO_LOG_OPTIONS,
    NEMO_REFUSAL_ANSWERS,
    NEMO_SKIP_INPUT_RAILS,
    REFUSAL_NEMO,
)
from app.core.config import settings
from app.services.guardrails import GuardrailVerdict

logger = logging.getLogger(__name__)


def enabled() -> bool:
    return bool(settings.GUARDRAILS_ENABLED and settings.GUARDRAILS_ENDPOINT_URL)


def request_options(check_input: bool = True) -> Dict[str, Any]:
    """The `guardrails` object of a chat request: our config, the rails log, and no input check when asked."""
    options: Dict[str, Any] = dict(NEMO_LOG_OPTIONS)
    if not check_input:
        options["rails"] = dict(NEMO_SKIP_INPUT_RAILS)
    return {"config_id": settings.GUARDRAILS_CONFIG_ID, "options": options}


def blocked(data: Dict[str, Any], content: Optional[str]) -> Optional[GuardrailVerdict]:
    """The verdict when NeMo stopped this request, else None. Only the rail's type and name are logged."""
    rail = _stopping_rail(data)
    if rail is not None:
        rail_type, name = rail
        logger.warning(NEMO_BLOCKED_LOG, rail_type, name)
        return GuardrailVerdict(category=NEMO_CATEGORY.format(type=rail_type, name=name), refusal=REFUSAL_NEMO)

    if content is not None and content.strip() in NEMO_REFUSAL_ANSWERS:  # a NeMo without the rails log
        logger.warning(NEMO_BLOCKED_LOG, "unknown", "refusal text")
        return GuardrailVerdict(category=GUARDRAIL_CATEGORY_NEMO, refusal=REFUSAL_NEMO)

    return None


def _stopping_rail(data: Dict[str, Any]):
    log = (data.get("guardrails") or {}).get("log") or {}
    for rail in log.get("activated_rails") or []:
        if isinstance(rail, dict) and rail.get("stop") and rail.get("type") != NEMO_GENERATION_RAIL:
            return str(rail.get("type", "")), str(rail.get("name", ""))
    return None


def label(category: str) -> str:
    """Which layer refused, for the answer shown to the owner: 'NeMo Guardrails: self check input'."""
    if category.startswith(NEMO_CATEGORY_PREFIX):
        return GUARDRAIL_LABEL_NEMO.format(rail=category.rsplit(":", 1)[-1])
    if category == GUARDRAIL_CATEGORY_NEMO:
        return GUARDRAIL_LABEL_NEMO.format(rail="refusal")
    return GUARDRAIL_LABEL_BACKEND.format(rule=category.replace("_", " "))
