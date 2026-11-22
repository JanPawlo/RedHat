"""
Guardrail layer around every LLM call.

1. Input rail: the user's question and chat history are checked for requests to do something illegal
   (money laundering, tax evasion, fraud, bribery, getting other people's data) and for prompt injection.
   A match is refused before the model is called.
2. Data rail: facts sent to the model (invoices, statements, notes) are data, not instructions.
   Instruction-like text inside them is replaced, so a crafted invoice cannot steer the model, and personal or
   banking identifiers are masked, so the model never sees (or repeats) a full PESEL, card number or IBAN.
3. Output rail: the answer is checked again for illegal how-to content, and personal or banking
   identifiers (PESEL, card numbers, full IBANs) are masked before the answer leaves the API.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Pattern

from app.const.guardrails import (
    CARD_NUMBER_MIN_DIGITS,
    CARD_NUMBER_PATTERN,
    DIACRITICS_MAP,
    GUARDRAIL_BLOCKED_LOG,
    GUARDRAIL_CATEGORY_PROMPT_INJECTION,
    GUARDRAIL_REDACTED_LOG,
    IBAN_PATTERN,
    IBAN_VISIBLE_TAIL,
    ILLEGAL_REQUEST_PATTERNS,
    INJECTION_PLACEHOLDER,
    PESEL_PATTERN,
    PESEL_WEIGHTS,
    PROMPT_INJECTION_PATTERNS,
    REDACTED_CARD,
    REDACTED_IBAN_PREFIX,
    REDACTED_IBAN_SUFFIX,
    REDACTED_PESEL,
    REFUSAL_BY_CATEGORY,
    REFUSAL_TEXTS,
    REFUSAL_UNSAFE_ANSWER,
    UNSAFE_ANSWER_PATTERNS,
)

logger = logging.getLogger(__name__)


def _compile(patterns: Iterable[str]) -> List[Pattern[str]]:
    return [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in patterns]


_ILLEGAL = {category: _compile(patterns) for category, patterns in ILLEGAL_REQUEST_PATTERNS.items()}
_INJECTION = _compile(PROMPT_INJECTION_PATTERNS)
_UNSAFE_ANSWER = _compile(UNSAFE_ANSWER_PATTERNS)
_PESEL = re.compile(PESEL_PATTERN)
_CARD = re.compile(CARD_NUMBER_PATTERN)
_IBAN = re.compile(IBAN_PATTERN)


@dataclass(frozen=True)
class GuardrailVerdict:
    category: str
    refusal: str


class GuardrailBlockedError(Exception):
    """Raised instead of calling the model; `refusal` is the answer shown to the user."""

    def __init__(self, verdict: GuardrailVerdict):
        super().__init__(verdict.category)
        self.category = verdict.category
        self.refusal = verdict.refusal


def normalize(text: str) -> str:
    without_polish = text.translate(DIACRITICS_MAP)
    decomposed = unicodedata.normalize("NFKD", without_polish)
    ascii_only = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", ascii_only).lower()


def _matches(patterns: List[Pattern[str]], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def check_request(texts: Iterable[str], rail: str) -> None:
    """Input rail: raises `GuardrailBlockedError` when any text asks for something illegal or tries to override the rules."""
    for text in texts:
        verdict = _classify(normalize(text))
        if verdict:
            logger.warning(GUARDRAIL_BLOCKED_LOG, rail, verdict.category)
            raise GuardrailBlockedError(verdict)


def _classify(text: str) -> Optional[GuardrailVerdict]:
    if _matches(_INJECTION, text):
        return GuardrailVerdict(GUARDRAIL_CATEGORY_PROMPT_INJECTION, REFUSAL_BY_CATEGORY[GUARDRAIL_CATEGORY_PROMPT_INJECTION])

    for category, patterns in _ILLEGAL.items():
        if _matches(patterns, text):
            return GuardrailVerdict(category, REFUSAL_BY_CATEGORY[category])

    return None


def sanitize_facts(value: Any) -> Any:
    """Data rail: walks the facts and replaces instruction-like strings, keeping the structure and all numbers."""
    if isinstance(value, dict):
        return {key: sanitize_facts(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [sanitize_facts(item) for item in value]

    if isinstance(value, str) and _matches(_INJECTION, normalize(value)):
        return INJECTION_PLACEHOLDER

    if isinstance(value, str):
        return redact(value)  # the model never sees a full PESEL, card number or IBAN, so it cannot repeat one

    return value


def check_answer(answer: str) -> str:
    """Output rail: refuses illegal how-to content and masks personal or banking identifiers."""
    if _matches(_UNSAFE_ANSWER, normalize(answer)):
        logger.warning(GUARDRAIL_BLOCKED_LOG, "answer", "unsafe_answer")
        return REFUSAL_UNSAFE_ANSWER

    return redact(answer)


def redact(text: str) -> str:
    redactions = 0

    def pesel(match: re.Match) -> str:
        nonlocal redactions
        if not _is_pesel(match.group()):
            return match.group()
        redactions += 1
        return REDACTED_PESEL

    def card(match: re.Match) -> str:
        nonlocal redactions
        digits = re.sub(r"\D", "", match.group())
        if len(digits) < CARD_NUMBER_MIN_DIGITS or not _passes_luhn(digits):
            return match.group()
        redactions += 1
        return REDACTED_CARD

    def iban(match: re.Match) -> str:
        nonlocal redactions
        compact = match.group().replace(" ", "")
        redactions += 1
        return f"{REDACTED_IBAN_PREFIX}{compact[-IBAN_VISIBLE_TAIL:]}{REDACTED_IBAN_SUFFIX}"

    result = _IBAN.sub(iban, text)
    result = _PESEL.sub(pesel, result)
    result = _CARD.sub(card, result)

    if redactions:
        logger.info(GUARDRAIL_REDACTED_LOG, redactions)

    return result


def _is_pesel(digits: str) -> bool:
    checksum = sum(int(digit) * weight for digit, weight in zip(digits, PESEL_WEIGHTS)) % 10
    return (10 - checksum) % 10 == int(digits[-1])


def _passes_luhn(digits: str) -> bool:
    total = 0
    for index, digit in enumerate(reversed(digits)):
        value = int(digit)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value

    return total % 10 == 0


def clean_history(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Drops earlier exchanges that the input rail would refuse (the user turn and the reply after it), and
    exchanges that were refused (the reply is a refusal text, e.g. from NeMo Guardrails), so one refused
    question does not block the rest of the chat and cannot be continued later.
    """
    cleaned: List[Dict[str, str]] = []
    skip_reply = False

    for turn in history:
        if turn["role"] == "assistant" and turn["content"].strip() in REFUSAL_TEXTS:
            # Refused later (by NeMo or the output rail): drop the refusal and the question it answered.
            if cleaned and cleaned[-1]["role"] == "user":
                cleaned.pop()
            logger.warning(GUARDRAIL_BLOCKED_LOG, "history", "refused_turn")
            skip_reply = False
            continue
        if turn["role"] == "user":
            skip_reply = _classify(normalize(turn["content"])) is not None
            if skip_reply:
                logger.warning(GUARDRAIL_BLOCKED_LOG, "history", "dropped_turn")
                continue
        elif skip_reply:
            skip_reply = False
            continue

        cleaned.append(turn)

    return cleaned
