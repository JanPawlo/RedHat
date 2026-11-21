"""
Runs the engine tools the model asks for while answering (memory/spec/silnik.md) and logs every call.

One `EngineToolRunner` serves one answer: it carries the request id, counts calls against the limit and keeps what
the model was shown, so the answer's guardrails can accept numbers that came from a tool. Results are compact and
rounded the same way as the card facts (`money`), so the model can quote them as they are; field names are plain
words, because qwen3-8b reuses them in its answer ("safety buffer" would fail the jargon check).
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.const.engine_tools import (
    AMOUNT_NOISE,
    TOOL_CAPABILITY_MAX_LENGTH,
    TOOL_ERROR_ARGUMENTS,
    TOOL_ERROR_FAILED,
    TOOL_ERROR_LIMIT,
    TOOL_ERROR_NO_ACCOUNT,
    TOOL_ERROR_UNKNOWN,
    TOOL_GET_FORECAST,
    TOOL_HORIZON_MAX_DAYS,
    TOOL_HORIZON_MIN_DAYS,
    TOOL_LOG_ARGUMENTS,
    TOOL_LOG_LIMIT,
    TOOL_LOG_NO_ACCOUNT,
    TOOL_LOG_UNKNOWN,
    TOOL_MAX_CALLS,
    TOOL_MAX_CHANGES,
    TOOL_MISSING_NAME,
    TOOL_NEED_MAX_LENGTH,
    TOOL_REPORT_GAP,
    TOOL_SIMULATE,
    TOOL_STATUS_ERROR,
    TOOL_STATUS_FAILED,
    TOOL_STATUS_INVALID,
    TOOL_STATUS_REJECTED,
    TOOL_STATUS_SUCCESS,
    TOOL_STATUS_UNSUPPORTED,
)
from app.const.forecast import SCENARIO_BASE, SCENARIO_NAMES
from app.managers import agent_engine_log_manager, forecast_manager
from app.schemas.forecast import CashChangeRequest, ForecastResponse, SimulationResponse
from app.services.card_templates import money

logger = logging.getLogger(__name__)

# (result for the model, status, log message, capability gap to record)
ToolOutcome = Tuple[Dict[str, Any], str, Optional[str], Optional[Dict[str, str]]]


class _ForecastArgs(BaseModel):
    account_id: Optional[UUID] = None
    horizon_days: Optional[int] = Field(default=None, ge=TOOL_HORIZON_MIN_DAYS, le=TOOL_HORIZON_MAX_DAYS)


class _SimulationArgs(_ForecastArgs):
    changes: List[CashChangeRequest] = Field(min_length=1, max_length=TOOL_MAX_CHANGES)


class _CapabilityArgs(BaseModel):
    capability: str = Field(min_length=1, max_length=TOOL_CAPABILITY_MAX_LENGTH)
    business_need: str = Field(min_length=1, max_length=TOOL_NEED_MAX_LENGTH)


class EngineToolRunner:
    """Executes tool calls for one model answer; pass it as the `run_tool` callback of `llm.chat_with_tools`."""

    def __init__(self, db: AsyncSession, user_id: Optional[UUID] = None, action_id: Optional[UUID] = None):
        self.db = db
        self.user_id = user_id
        self.action_id = action_id
        self.request_id = uuid4()
        self.calls: List[Dict[str, Any]] = []
        self._executed = 0

    @property
    def results_text(self) -> str:
        """Everything the tools returned, for the guardrails' list of allowed numbers and dates."""
        return " ".join(json.dumps(call["result"], default=str, ensure_ascii=False) for call in self.calls)

    async def __call__(self, name: str, raw_arguments: Any) -> Dict[str, Any]:
        started = time.perf_counter()
        if self._executed >= TOOL_MAX_CALLS:
            outcome: ToolOutcome = ({"error": TOOL_ERROR_LIMIT}, TOOL_STATUS_REJECTED, TOOL_LOG_LIMIT, None)
        else:
            self._executed += 1
            try:
                async with self.db.begin_nested():
                    outcome = await _run(self.db, name, raw_arguments)
            except Exception:  # one broken tool call must not break the answer
                logger.exception("Engine tool %s failed", name)
                outcome = ({"error": TOOL_ERROR_FAILED}, TOOL_STATUS_ERROR, TOOL_ERROR_FAILED, None)

        result, status, error_message, gap = outcome
        duration_ms = int((time.perf_counter() - started) * 1000)
        arguments = _arguments(raw_arguments)
        await self._log(name, arguments, result, status, error_message, duration_ms, gap)
        self.calls.append({"tool": name, "arguments": arguments, "result": result, "status": status, "duration_ms": duration_ms})
        return result

    async def _log(self, name, arguments, result, status, error_message, duration_ms, gap) -> None:
        ids = {"request_id": self.request_id, "action_id": self.action_id, "user_id": self.user_id}
        if gap:
            await agent_engine_log_manager.record_capability_request(self.db, **ids, **gap)
        await agent_engine_log_manager.record_engine_call(
            self.db,
            **ids,
            tool_name=name or TOOL_MISSING_NAME,
            arguments=arguments if isinstance(arguments, dict) else {"invalid_arguments": arguments},
            result=result,
            status=status,
            error_message=error_message,
            duration_ms=duration_ms,
        )


async def _run(db: AsyncSession, name: str, raw_arguments: Any) -> ToolOutcome:
    try:
        arguments = _tolerant(json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments)

        if name == TOOL_REPORT_GAP:
            request = _CapabilityArgs.model_validate(arguments)
            gap = {"capability": request.capability, "business_need": request.business_need}
            return {"recorded_for_review": True, **gap}, TOOL_STATUS_SUCCESS, None, gap

        if name == TOOL_GET_FORECAST:
            request = _ForecastArgs.model_validate(arguments or {})
            forecast = await forecast_manager.get_forecast(db, request.account_id, request.horizon_days)
            if forecast is None:
                return {"error": TOOL_ERROR_NO_ACCOUNT}, TOOL_STATUS_FAILED, TOOL_LOG_NO_ACCOUNT, None
            return forecast_summary(forecast), TOOL_STATUS_SUCCESS, None, None

        if name == TOOL_SIMULATE:
            request = _SimulationArgs.model_validate(arguments)
            result = await forecast_manager.simulate_forecast(db, request.account_id, request.horizon_days, request.changes)
            if result is None:
                return {"error": TOOL_ERROR_NO_ACCOUNT}, TOOL_STATUS_FAILED, TOOL_LOG_NO_ACCOUNT, None
            return simulation_summary(result), TOOL_STATUS_SUCCESS, None, None

        return {"error": TOOL_ERROR_UNKNOWN}, TOOL_STATUS_UNSUPPORTED, TOOL_LOG_UNKNOWN, None
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
        return {"error": TOOL_ERROR_ARGUMENTS}, TOOL_STATUS_INVALID, TOOL_LOG_ARGUMENTS, None


def _percent(value) -> int:
    return int(round(float(value) * 100))


def _lowest(forecast: ForecastResponse, scenario: str) -> str:
    indicators = forecast.scenarios[scenario].indicators
    return f"{money(indicators.lowest_balance, forecast.currency)} on {indicators.lowest_balance_date}"


def _below_minimum(forecast: ForecastResponse) -> str:
    broken = forecast.scenarios[SCENARIO_BASE].indicators.first_below_buffer_date
    return str(broken) if broken else "never"


def forecast_summary(forecast: ForecastResponse) -> Dict[str, Any]:
    return {
        "forecast_start": str(forecast.as_of),
        "balance_today": money(forecast.opening_balance, forecast.currency),
        "minimum_you_want_to_keep": money(forecast.safety_buffer, forecast.currency),
        "days_ahead": forecast.horizon_days,
        "confidence_percent": _percent(forecast.confidence),
        "lowest_balance": {name: _lowest(forecast, name) for name in SCENARIO_NAMES if name in forecast.scenarios},
        "first_day_below_your_minimum": _below_minimum(forecast),
        "approved_decisions_included": [decision.title for decision in forecast.decisions_applied],
    }


def simulation_summary(result: SimulationResponse) -> Dict[str, Any]:
    before, after = result.baseline, result.simulated
    return {
        "lowest_balance_change": money(result.lowest_balance_change, after.currency),
        "lowest_balance_before": _lowest(before, SCENARIO_BASE),
        "lowest_balance_after": _lowest(after, SCENARIO_BASE),
        "first_day_below_your_minimum_before": _below_minimum(before),
        "first_day_below_your_minimum_after": _below_minimum(after),
        "confidence_before_percent": _percent(before.confidence),
        "confidence_after_percent": _percent(after.confidence),
    }


def _tolerant(arguments: Any) -> Any:
    """Accept what the model writes from FACTS: "€1,600" as 1600, and no account id unless it is a real UUID."""
    if not isinstance(arguments, dict):
        return arguments
    arguments = dict(arguments)
    try:
        UUID(str(arguments.get("account_id")))
    except ValueError:
        arguments.pop("account_id", None)
    changes = arguments.get("changes")
    if isinstance(changes, list):
        arguments["changes"] = [
            {**change, "amount": plain_amount(change.get("amount"))} if isinstance(change, dict) else change
            for change in changes
        ]
    return arguments


def plain_amount(raw: Any) -> Any:
    """ "-€1,600.50" → "-1600.50"; "1.600,50" → "1600.50"; anything else is returned for the schema to reject."""
    if not isinstance(raw, str):
        return raw
    text = raw.replace("−", "-")
    for noise in AMOUNT_NOISE:
        text = text.replace(noise, "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    elif "," in text:
        whole, _, part = text.rpartition(",")
        text = text.replace(",", "") if len(part) == 3 else f"{whole.replace(',', '')}.{part}"
    return text


def _arguments(raw_arguments: Any) -> Any:
    try:
        return json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
    except json.JSONDecodeError:
        return {"invalid_arguments": True}
