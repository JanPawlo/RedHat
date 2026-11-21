"""Advisor answer without the model: quotes the engine's facts when the model is busy or too slow."""
from typing import Any, Dict, List, Optional

from app.const.llm_limits import (
    ADVISOR_FALLBACK_BALANCE,
    ADVISOR_FALLBACK_BEST_DATE,
    ADVISOR_FALLBACK_DEFAULT_DAYS,
    ADVISOR_FALLBACK_INTRO,
    ADVISOR_FALLBACK_LOWEST_BELOW,
    ADVISOR_FALLBACK_LOWEST_OK,
    ADVISOR_FALLBACK_OUTRO,
    ADVISOR_FALLBACK_SPEND_NOW,
)


def busy_advisor_answer(facts: Dict[str, Any]) -> str:
    currency = facts.get("currency") or ""

    sentences: List[Optional[str]] = [
        ADVISOR_FALLBACK_INTRO,
        _balance_sentence(facts, currency),
        _lowest_sentence(facts.get("lowest_balance_next_days"), currency),
        *_spending_sentences(facts.get("spending_room"), currency),
        ADVISOR_FALLBACK_OUTRO,
    ]

    return " ".join(sentence for sentence in sentences if sentence)


def _money(value: Any, currency: str) -> Optional[str]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None

    return f"{value:,.2f} {currency}".strip()


def _balance_sentence(facts: Dict[str, Any], currency: str) -> Optional[str]:
    balance = _money(facts.get("bank_balance"), currency)
    buffer = _money(facts.get("safety_buffer"), currency)
    if not balance or not buffer:
        return None

    return ADVISOR_FALLBACK_BALANCE.format(balance=balance, buffer=buffer)


def _lowest_sentence(lowest: Any, currency: str) -> Optional[str]:
    if not isinstance(lowest, dict):
        return None

    amount = _money(lowest.get("amount"), currency)
    date = lowest.get("date")
    if not amount or not date:
        return None

    days = lowest.get("days") or ADVISOR_FALLBACK_DEFAULT_DAYS
    short = _money(lowest.get("short_of_buffer_by"), currency)
    if lowest.get("is_below_safety_buffer"):
        return ADVISOR_FALLBACK_LOWEST_BELOW.format(days=days, amount=amount, date=date, short=short) if short else None

    return ADVISOR_FALLBACK_LOWEST_OK.format(days=days, amount=amount, date=date)


def _spending_sentences(room: Any, currency: str) -> List[str]:
    if not isinstance(room, dict):
        return []

    sentences = []

    now = _money(room.get("can_spend_now"), currency)
    if now:
        sentences.append(ADVISOR_FALLBACK_SPEND_NOW.format(amount=now))

    best = _money(room.get("can_spend_on_best_date"), currency)
    if best and room.get("best_date_to_pay"):
        sentences.append(ADVISOR_FALLBACK_BEST_DATE.format(date=room["best_date_to_pay"], amount=best))

    return sentences
