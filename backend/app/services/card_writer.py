"""
The AI step of card generation: qwen3-8b writes each card's text from the template's slots and ranks the cards.

Every answer goes through `card_guardrails`. A card with violations gets one repair round (the model sees what it
broke); fields that still fail are replaced by the template's fallback text, and a card that still fails as a whole
is written entirely from the fallback. The ranking may only reorder cards inside their tier and falls back to the
engine score. If the model is unreachable once, the rest of the run uses fallbacks without waiting on it again.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.const.card_templates import (
    CARD_CHAT_MAX_TOKENS,
    CARD_CHAT_SYSTEM_PROMPT,
    CHAT_HISTORY_TURNS,
    COPY_FIELDS,
    GAP_CLOSED_CLAIMS,
    COPY_MAX_TOKENS,
    COPY_SOURCE_FALLBACK,
    COPY_SOURCE_MIXED,
    COPY_SOURCE_MODEL,
    COPY_SYSTEM_PROMPT,
    COPY_TEMPERATURE,
    COPY_USER_PROMPT,
    EFFECT_NOTE_CLOSED,
    EFFECT_NOTE_OPEN,
    EXPLAIN_REPAIR_PROMPT,
    FIELD_SPECS,
    JARGON_PLAIN_ALTERNATIVES,
    MODEL_CONCURRENCY,
    RANK_MAX_TOKENS,
    RANK_SOURCE_FALLBACK,
    RANK_SOURCE_MODEL,
    RANK_SYSTEM_PROMPT,
    RANK_TEMPERATURE,
    RANK_USER_PROMPT,
    REPAIR_ATTEMPTS,
    REPAIR_PROMPT,
)
from app.const.engine_tools import CARD_CHAT_TOOLS, ENGINE_TOOLS_PROMPT, TOOL_RESULTS_NOTE
from app.const.llm import SAFETY_RULES
from app.services.card_guardrails import (
    CheckContext,
    check_answer,
    check_card,
    check_rank_reason,
    check_ranking,
    enforce_tiers,
    sentences,
)
from app.services.card_templates import CardTemplate, fill
from app.services.guardrails import check_answer as mask_answer, clean_history, sanitize_facts
from app.services.llm import LLMUnavailableError, ToolRunner, chat, chat_with_tools

logger = logging.getLogger(__name__)

THINK_PATTERN = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)

# Schemas only guarantee valid JSON with the right keys. No maxLength: length limits make vLLM's guided decoding build
# huge grammars that can stall the shared model server; lengths are checked by the guardrails instead.
COPY_SCHEMA = {
    "type": "object",
    "properties": {name: {"type": "string"} for name in COPY_FIELDS},
    "required": list(COPY_FIELDS),
    "additionalProperties": False,
}
RANK_SCHEMA = {
    "type": "object",
    "properties": {
        "ranking": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["id", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["ranking"],
    "additionalProperties": False,
}


class ModelSession:
    """Shared by one generation run: limits parallel requests and stops calling a model that is down."""

    def __init__(self, concurrency: int = MODEL_CONCURRENCY):
        self.available = True
        self.semaphore = asyncio.Semaphore(concurrency)
        self.calls = 0

    async def ask(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int,
        temperature: float,
        schema: Optional[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        run_tool: Optional[ToolRunner] = None,
        user_key: Optional[str] = None,
    ) -> Optional[str]:
        """One answer (with `tools`: possibly a few calls); None when the model is down."""
        if not self.available:
            return None

        async with self.semaphore:
            if not self.available:
                return None
            try:
                self.calls += 1
                if tools and run_tool:
                    return await chat_with_tools(messages, tools, run_tool, max_tokens, temperature, user_key=user_key)
                return await chat(messages, max_tokens, temperature, schema, user_key=user_key)
            except LLMUnavailableError as exc:
                logger.warning("Model unavailable, using template fallbacks for the rest of this run: %s", exc)
                self.available = False
                return None


# ---------------------------------------------------------------- copy

@dataclass
class CopyRequest:
    key: str
    template: CardTemplate
    slots: Dict[str, str]
    check: CheckContext


@dataclass
class CardCopy:
    fields: Dict[str, str]
    source: str
    violations: Dict[str, List[str]] = field(default_factory=dict)  # what the model got wrong (kept for audit)


def fallback_copy(request: CopyRequest) -> Dict[str, str]:
    fallback = request.template.fallback
    return {
        "title": fill(fallback.title, request.slots),
        "proposal": fill(fallback.proposal, request.slots),
        "explanation": fill(fallback.explanation, request.slots),
    }


def copy_messages(request: CopyRequest) -> List[Dict[str, str]]:
    jargon = ", ".join(f"{term} -> {plain}" for term, plain in JARGON_PLAIN_ALTERNATIVES.items())
    facts = "\n".join(f"- {key}: {value}" for key, value in request.slots.items() if value)
    guardrails = request.template.guardrails
    required = [request.slots[key] for key in guardrails.must_mention if request.slots.get(key)]
    fields = "\n".join(
        f"- {name} (at most {FIELD_SPECS[name]['max_chars']} characters): {FIELD_SPECS[name]['style']} "
        f"Example of the style only: \"{FIELD_SPECS[name]['example']}\""
        for name in COPY_FIELDS
    )
    extra = []
    if guardrails.title_must_mention:
        extra.append("The title must name: " + ", ".join(request.slots[k] for k in guardrails.title_must_mention if request.slots.get(k)) + ".")
    for group in guardrails.required_phrases:
        extra.append(f"The proposal or explanation must say plainly something like '{group[0]}'.")

    user = COPY_USER_PROMPT.format(
        template_name=request.template.name,
        brief=request.template.brief,
        facts=facts,
        required=", ".join(required) or "-",
        effect_note=_effect_note(request.slots),
        fields=fields + ("\n" + "\n".join(extra) if extra else ""),
    )
    return [{"role": "system", "content": COPY_SYSTEM_PROMPT.format(jargon=jargon)}, {"role": "user", "content": user}]


def _effect_note(slots: Dict[str, str]) -> str:
    kept = slots.get("minimum_kept_with_card")
    if kept == "no" and slots.get("balance_gain"):
        return EFFECT_NOTE_OPEN
    if kept == "yes":
        return EFFECT_NOTE_CLOSED
    return ""


def parse_json(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    text = THINK_PATTERN.sub("", raw).strip()
    match = JSON_PATTERN.search(text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _clean(value: Any) -> str:
    return " ".join(str(value).split()) if isinstance(value, (str, int, float)) else ""


def _violations(request: CopyRequest, fields: Dict[str, str]) -> Dict[str, List[str]]:
    guardrails = request.template.guardrails
    return check_card(fields, request.check, guardrails.must_mention, guardrails.title_must_mention, guardrails.required_phrases)


async def write_copy(session: ModelSession, request: CopyRequest) -> CardCopy:
    messages = copy_messages(request)
    raw = await session.ask(messages, COPY_MAX_TOKENS, COPY_TEMPERATURE, COPY_SCHEMA)
    data = parse_json(raw)
    if data is None:
        return CardCopy(fallback_copy(request), COPY_SOURCE_FALLBACK, {"model": ["no valid JSON answer"]} if raw else {})

    fields = {name: _clean(data.get(name, "")) for name in COPY_FIELDS}
    problems = _violations(request, fields)
    first_problems = {name: list(found) for name, found in problems.items() if found}

    for _ in range(REPAIR_ATTEMPTS):
        broken = [name for name, found in problems.items() if found]
        if not broken:
            break
        fields, problems = await _repair(session, request, messages, raw or "", fields, problems, broken)

    return _finish(request, fields, problems, first_problems)


async def _repair(session, request, messages, raw, fields, problems, broken):
    listing = "\n".join(f"- {name}: {'; '.join(problems[name])}" for name in broken)
    repair = [*messages, {"role": "assistant", "content": raw}, {"role": "user", "content": REPAIR_PROMPT.format(violations=listing, fields=", ".join(broken))}]
    data = parse_json(await session.ask(repair, COPY_MAX_TOKENS, COPY_TEMPERATURE, COPY_SCHEMA))
    if data:
        fields = {**fields, **{name: _clean(data[name]) for name in broken if _clean(data.get(name))}}

    return fields, _violations(request, fields)


def _finish(request: CopyRequest, fields, problems, first_problems) -> CardCopy:
    broken = [name for name, found in problems.items() if found]
    if not broken:
        return CardCopy(fields, COPY_SOURCE_MODEL, first_problems)

    fallback = fallback_copy(request)
    mixed = {name: fallback[name] if name in broken else fields[name] for name in COPY_FIELDS}
    if not any(_violations(request, mixed).values()):
        return CardCopy(mixed, COPY_SOURCE_MIXED, first_problems)

    return CardCopy(fallback, COPY_SOURCE_FALLBACK, first_problems)


async def write_all(session: ModelSession, requests: Sequence[CopyRequest]) -> Dict[str, CardCopy]:
    results = await asyncio.gather(*(write_copy(session, request) for request in requests))
    return {request.key: result for request, result in zip(requests, results)}


# ---------------------------------------------------------------- ranking

@dataclass
class RankItem:
    key: str
    summary: str  # one deterministic line: template name + the card's fallback title
    metrics: Dict[str, str]  # engine numbers and traits, already formatted
    tier: int
    score: float
    fallback_reason: str
    check: CheckContext


@dataclass
class Ranking:
    order: List[str]
    reasons: Dict[str, str]
    source: str
    violations: List[str] = field(default_factory=list)


def rank_messages(items: Sequence[RankItem], situation: str, labels: Dict[str, str]) -> List[Dict[str, str]]:
    actions = "\n".join(
        f"- id {labels[item.key]}: {item.summary}. " + "; ".join(f"{name}: {value}" for name, value in item.metrics.items())
        for item in items
    )
    user = RANK_USER_PROMPT.format(situation=situation, actions=actions)
    return [{"role": "system", "content": RANK_SYSTEM_PROMPT}, {"role": "user", "content": user}]


def fallback_ranking(items: Sequence[RankItem]) -> Ranking:
    order = [item.key for item in sorted(items, key=lambda item: (item.tier, -item.score))]
    return Ranking(order, {item.key: item.fallback_reason for item in items}, RANK_SOURCE_FALLBACK)


async def rank(session: ModelSession, items: Sequence[RankItem], situation: str) -> Ranking:
    if len(items) <= 1:
        return fallback_ranking(items)

    labels = {item.key: chr(ord("A") + index) for index, item in enumerate(items)}
    by_label = {label: key for key, label in labels.items()}
    messages = rank_messages(items, situation, labels)

    data = parse_json(await session.ask(messages, RANK_MAX_TOKENS, RANK_TEMPERATURE, RANK_SCHEMA))
    entries = _rank_entries(data)
    problems = check_ranking([entry[0] for entry in entries], list(by_label))
    if entries and problems:
        retry = [*messages, {"role": "assistant", "content": json.dumps(data)},
                 {"role": "user", "content": f"Your ranking {'; '.join(problems)}. Return every id exactly once."}]
        entries = _rank_entries(parse_json(await session.ask(retry, RANK_MAX_TOKENS, RANK_TEMPERATURE, RANK_SCHEMA)))
        problems = check_ranking([entry[0] for entry in entries], list(by_label))

    if not entries or problems:
        result = fallback_ranking(items)
        result.violations = problems or (["no valid JSON answer"] if session.available else [])
        return result

    return _model_ranking(items, entries, by_label)


def _rank_entries(data: Optional[Dict[str, Any]]) -> List[Tuple[str, str]]:
    ranking = (data or {}).get("ranking")
    if not isinstance(ranking, list):
        return []
    return [(_clean(entry.get("id")).upper(), _clean(entry.get("reason"))) for entry in ranking if isinstance(entry, dict)]


def _model_ranking(items: Sequence[RankItem], entries, by_label) -> Ranking:
    by_key = {item.key: item for item in items}
    order = [by_label[label] for label, _ in entries]
    tiers = {item.key: item.tier for item in items}
    enforced = enforce_tiers(order, tiers)

    reasons: Dict[str, str] = {}
    violations: List[str] = []
    for label, reason in entries:
        key = by_label[label]
        problems = check_rank_reason(reason, by_key[key].check)
        if problems:
            violations.append(f"{label}: {'; '.join(problems)}")
            reasons[key] = by_key[key].fallback_reason
        else:
            reasons[key] = reason

    if enforced != order:
        violations.append("order changed to keep free actions that close the gap ahead of paid ones")

    return Ranking(enforced, reasons, RANK_SOURCE_MODEL, violations)


# ---------------------------------------------------------------- "Ask why" chat answers

async def answer_question(
    facts: Dict[str, Any],
    question: str,
    fallback: str,
    history: Sequence[Dict[str, str]] = (),
    slots: Optional[Dict[str, str]] = None,
    closes_gap: Optional[bool] = None,
    run_tool: Optional[ToolRunner] = None,
    user_key: Optional[str] = None,
) -> Tuple[str, str]:
    """
    (answer, source) for a free question about a card. The model sees the card's facts, what happens after approving
    and the earlier turns of this chat; with `run_tool` it may ask the engine for a what-if (`CARD_CHAT_TOOLS`).
    The answer must pass the card guardrails (numbers from the facts or the tool results, balance claims, no
    overclaiming), must not repeat earlier answers, and is masked for personal or bank identifiers.
    """
    session = ModelSession(concurrency=1)
    safe_facts = sanitize_facts(facts)
    facts_text = json.dumps(safe_facts, default=str, ensure_ascii=False)
    turns = clean_history(list(history)[-CHAT_HISTORY_TURNS:])
    earlier = " ".join(turn["content"] for turn in turns if turn.get("role") == "assistant")
    tool_results: List[Dict[str, Any]] = []

    async def run_and_keep(name: str, arguments: Any) -> Dict[str, Any]:
        result = await run_tool(name, arguments)
        tool_results.append(result)
        return result

    messages = [
        {"role": "system", "content": CARD_CHAT_SYSTEM_PROMPT + SAFETY_RULES + (ENGINE_TOOLS_PROMPT if run_tool else "")},
        *turns,
        {"role": "user", "content": f"FACTS:\n{facts_text}\n\nQUESTION:\n{question}"},
    ]

    tools = CARD_CHAT_TOOLS if run_tool else None
    answer = _clean_answer(await session.ask(messages, CARD_CHAT_MAX_TOKENS, COPY_TEMPERATURE, None, tools, run_and_keep, user_key))
    if not session.available:
        raise LLMUnavailableError("model unavailable")

    # Built after the tools ran: numbers the engine returned are as allowed as the ones in FACTS.
    check = CheckContext(
        slots={key: str(value) for key, value in (slots or {}).items()},
        currency=_currency(facts),
        extra_allowed_text=f"{facts_text} {json.dumps(tool_results, default=str, ensure_ascii=False)} {question} {earlier}",
        extra_forbidden=() if closes_gap or closes_gap is None and not slots else GAP_CLOSED_CLAIMS,
    )
    problems = [*check_answer(answer, check), *_repeats(answer, earlier)]
    if problems:
        retry = [*messages, {"role": "assistant", "content": answer},
                 {"role": "user", "content": _repair_request(problems, tool_results)}]
        answer = _clean_answer(await session.ask(retry, CARD_CHAT_MAX_TOKENS, COPY_TEMPERATURE, None, user_key=user_key))
        problems = [*check_answer(answer, check), *_repeats(answer, earlier)]

    if problems:
        logger.info("Chat answer failed guardrails, using the deterministic answer: %s", problems)
        return fallback, "guardrail_fallback"

    return mask_answer(answer), "model"


def _repair_request(problems: List[str], tool_results: List[Dict[str, Any]]) -> str:
    request = EXPLAIN_REPAIR_PROMPT.format(violations="; ".join(problems))
    if tool_results:
        request += "\n" + TOOL_RESULTS_NOTE.format(results=json.dumps(tool_results, default=str, ensure_ascii=False))
    return request


def _repeats(answer: str, earlier: str) -> List[str]:
    """Most of the answer was already said in this chat (word for word). Repeating one fact that answers the new
    question is fine; an answer that is mostly a rerun of the last one is not."""
    said = {" ".join(part.lower().split()) for part in sentences(earlier)}
    parts = sentences(answer)
    repeated = [part for part in parts if " ".join(part.lower().split()) in said]
    if parts and len(repeated) * 2 > len(parts):
        return ["repeats what you already said earlier in this chat; answer only the new question"]
    return []


def _clean_answer(raw: Optional[str]) -> str:
    return " ".join(THINK_PATTERN.sub("", raw or "").replace("<think>", "").replace("</think>", "").split())


def _currency(facts: Dict[str, Any]) -> str:
    text = json.dumps(facts, default=str, ensure_ascii=False)
    for code, symbol in (("EUR", "€"), ("USD", "$"), ("GBP", "£")):
        if symbol in text:
            return code
    return "PLN" if "PLN" in text else "EUR"
