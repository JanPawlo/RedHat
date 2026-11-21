"""
Decision cards from card templates (memory/spec/szablony-kart.md).

Flow of `generate_cards`: forecast context → goals → each template's candidates → engine simulation of every
candidate → filter and engine score → shortlist per template → the AI writes the text (with guardrails) → the AI
ranks (inside fixed tiers) → cards are created or updated; template cards that no longer apply are marked stale.
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.const.action import ACTION_STATUS_PENDING, EXECUTION_MODE_SIMULATED
from app.const.card_templates import (
    CERTAINTY_COUNTERPARTY,
    CERTAINTY_OWN,
    CERTAINTY_WEIGHT,
    COPY_SOURCE_FALLBACK,
    DECK_MAX_CARDS,
    EXPLAIN_SOURCE_TEMPLATE,
    GAP_CLOSED_CLAIMS,
    OTHER_PARTY_AGREEMENT_PHRASES,
    GOAL_CLOSE_GAP,
    GOAL_SAVE_MONEY,
    RELATIONSHIP_PENALTY,
    STALE_KEY,
    TEMPLATE_KEY,
    TIER_COSTLY,
    TIER_DEFAULT,
    TIER_FREE_CLOSES_GAP,
    WHY_QUESTION_PREFIX,
)
from app.const.cards import (
    AGENT_DISPLAY,
    BAR_MAX_HEIGHT,
    BAR_MIN_HEIGHT,
    CARD_HORIZON_DAYS,
    CARD_SOURCES,
    CARD_WEEKS,
    CONFIDENCE_METHOD,
    DEFAULT_AGENT_DISPLAY,
    EXPLAIN_FALLBACK_MODEL,
    MAIL_KEY,
    NEXT_SUB_KEY,
    PRIORITY_KEY,
    RESPONSE_SOURCE_FALLBACK,
    RESPONSE_SOURCE_MODEL,
    RESULT_SUFFIX,
    SWIPE_LEFT_KEY,
    SWIPE_RIGHT_KEY,
)
from app.const.forecast import CASH_CHANGES_KEY, CHANGE_AMOUNT_KEY, CHANGE_DAY_OFFSET_KEY, CHANGE_LABEL_KEY, SCENARIO_BASE
from app.const.llm import UNKNOWN_MODEL_NAME
from app.core.config import settings
from app.managers.action_manager import get_action
from app.managers.forecast_manager import ForecastContext, card_changes, load_context, preview_result
from app.models.action import AgentAction
from app.models.invoice import Invoice
from app.models.transaction import Transaction
from app.schemas.action import ExplainActionResponse
from app.services.card_guardrails import CheckContext, sanitize_untrusted
from app.services.card_templates import (
    Candidate,
    CardTemplate,
    InvoiceView,
    LatePayerView,
    TEMPLATES_BY_KEY,
    TemplateContext,
    active_goals,
    day_month,
    fill,
    money,
    templates_for,
)
from app.services.card_writer import CardCopy, CopyRequest, ModelSession, RankItem, Ranking, rank, write_all, answer_question
from app.services.forecast_engine import SimulationResult, build_forecast, confidence_grid, weekly_lows
from app.services.llm import LLMUnavailableError

logger = logging.getLogger(__name__)

CENT = Decimal("0.01")
HUNDRED = Decimal("100")
ZERO = Decimal("0")
NAME_SLOTS = ("counterparty", "customer", "supplier", "service", "item", "document")
YES, NO = "yes", "no"


# ---------------------------------------------------------------- demo reset

async def reset_decisions(db: AsyncSession) -> int:
    """Set every decided card back to pending, so the demo deck starts full again."""
    query = update(AgentAction).where(AgentAction.status != ACTION_STATUS_PENDING).values(status=ACTION_STATUS_PENDING, user_feedback=None)
    result = await db.execute(query)
    return result.rowcount or 0


# ---------------------------------------------------------------- generation

@dataclass
class Evaluated:
    template: CardTemplate
    candidate: Candidate
    result: SimulationResult
    closes_gap: bool
    tier: int
    score: float

    @property
    def dedupe_key(self) -> str:
        return self.candidate.dedupe_key(self.template)

    @property
    def improvement(self) -> Decimal:
        return self.result.lowest_balance_change


async def generate_cards(db: AsyncSession) -> Dict[str, Any]:
    """Find, simulate, write and rank cards for what the engine sees now; existing cards are updated, not duplicated."""
    context = await load_context(db, None, CARD_HORIZON_DAYS)
    if not context:
        return {"created": 0, "skipped": ["No primary bank account"]}

    template_context = await build_template_context(db, context)
    goals = active_goals(template_context)
    evaluated = shortlist([
        item
        for template in templates_for(goals)
        for candidate in template.detect(template_context)
        for item in [evaluate(template_context, template, candidate)]
        if item
    ])

    existing = await _existing(db, [item.dedupe_key for item in evaluated])
    live = [item for item in evaluated if _is_open(existing.get(item.dedupe_key))]
    session = ModelSession()

    copies = await write_all(session, [
        _copy_request(item, evaluated, template_context)
        for item in live
        if _needs_copy(existing.get(item.dedupe_key), item)
    ])
    ranking = await rank(session, [_rank_item(item, template_context) for item in live], situation(template_context))

    counts = _save(db, live, existing, copies, ranking, template_context)
    counts["stale"] = await _mark_stale(db, {item.dedupe_key for item in live})
    await db.flush()

    return {
        **counts,
        "skipped": [],
        "goals": goals,
        "candidates": len(evaluated),
        "model_calls": session.calls,
        "model_available": session.available,
        "copy_sources": {key: copy.source for key, copy in copies.items()},
        "rank_source": ranking.source,
        "rank_notes": ranking.violations,
    }


async def build_template_context(db: AsyncSession, context: ForecastContext) -> TemplateContext:
    planned = tuple(context.planned_changes)
    company = context.company
    owner = (company.settings or {}).get("owner_name", "The owner") if company else "The owner"

    return TemplateContext(
        inputs=context.inputs,
        planned=planned,
        baseline=build_forecast(context.inputs, planned),
        currency=context.account.currency,
        owner_name=str(owner),
        company_name=company.name if company else "",
        invoices=tuple(await _open_invoices(db)),
        late_payers=tuple(LatePayerView(**late.model_dump()) for late in context.late_payers),
        payment_counts=await _payment_counts(db, context),
        planned_expenses=context.planned_expenses,
    )


async def _open_invoices(db: AsyncSession) -> List[InvoiceView]:
    query = select(Invoice).where(Invoice.is_paid.is_(False), Invoice.invoice_type.in_(("incoming_expense", "outgoing_revenue"))).order_by(Invoice.due_date)
    return [
        InvoiceView(
            number=invoice.invoice_number,
            counterparty=invoice.counterparty_name,
            is_revenue=invoice.invoice_type == "outgoing_revenue",
            amount=invoice.gross_amount,
            currency=invoice.currency,
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
            early_discount_percent=invoice.early_discount_percent,
            early_discount_days=invoice.early_discount_days,
        )
        for invoice in (await db.execute(query)).scalars().all()
    ]


async def _payment_counts(db: AsyncSession, context: ForecastContext) -> Dict[str, int]:
    query = select(func.lower(Transaction.counterparty_name), func.count(Transaction.id)).where(
        Transaction.account_id == context.account.id, Transaction.amount < 0
    ).group_by(func.lower(Transaction.counterparty_name))
    return {" ".join(name.split()): count for name, count in (await db.execute(query)).all() if name}


def evaluate(context: TemplateContext, template: CardTemplate, candidate: Candidate) -> Optional[Evaluated]:
    """Simulate one candidate; drop it when it does not help or would create a gap that is not there."""
    candidate.slots = safe_slots(candidate.slots)
    result = context.simulate(candidate.changes)
    before = result.baseline.scenarios[SCENARIO_BASE].indicators
    after = result.simulated.scenarios[SCENARIO_BASE].indicators

    if after.first_below_buffer_date and not before.first_below_buffer_date:
        return None
    if GOAL_CLOSE_GAP in template.goals and context.breach_date and result.lowest_balance_change <= ZERO:
        if not template.allow_zero_effect and template.goals == (GOAL_CLOSE_GAP,):
            return None

    closes_gap = bool(context.breach_date) and not after.first_below_buffer_date
    _add_effect_slots(candidate, context, result)
    tier = card_tier(template, candidate, closes_gap)
    return Evaluated(template, candidate, result, closes_gap, tier, engine_score(context, template, candidate, result, closes_gap))


def safe_slots(slots: Dict[str, str]) -> Dict[str, str]:
    """Names come from statements and invoices: clean them before they reach a prompt or a card."""
    cleaned = dict(slots)
    for key in NAME_SLOTS:
        if key in cleaned:
            cleaned[key] = sanitize_untrusted(cleaned[key])[0]
    return cleaned


def _add_effect_slots(candidate: Candidate, context: TemplateContext, result: SimulationResult) -> None:
    after = result.simulated.scenarios[SCENARIO_BASE].indicators
    candidate.slots["lowest_balance_with_card"] = context.m(after.lowest_balance)
    candidate.slots["lowest_date_with_card"] = day_month(after.lowest_balance_date)
    candidate.slots["minimum_kept_with_card"] = NO if after.first_below_buffer_date else YES
    if result.lowest_balance_change > ZERO:
        candidate.slots["balance_gain"] = context.m(result.lowest_balance_change)


def card_tier(template: CardTemplate, candidate: Candidate, closes_gap: bool) -> int:
    """Hard order the model cannot change: free own actions that close the gap first, paid bank products last."""
    if candidate.cost > ZERO and template.guardrails.bank_product:
        return TIER_COSTLY
    if closes_gap and template.traits.certainty == CERTAINTY_OWN:
        return TIER_FREE_CLOSES_GAP
    return TIER_DEFAULT


def engine_score(context: TemplateContext, template: CardTemplate, candidate: Candidate, result: SimulationResult, closes_gap: bool) -> float:
    """Deterministic ranking score: effect on the gap, certainty and relationship risk, minus cost."""
    gap = max(context.buffer - context.pessimistic.lowest_balance, context.buffer - context.base.lowest_balance, ZERO)
    scale = gap if gap > ZERO else max(context.buffer, Decimal("1"))
    effect = min(max(result.lowest_balance_change, ZERO) / scale, Decimal("1"))
    risk = candidate.relationship_risk or template.traits.relationship_risk
    weight = CERTAINTY_WEIGHT[template.traits.certainty] * (1 - RELATIONSHIP_PENALTY[risk])
    cost_share = min(candidate.cost / max(result.lowest_balance_change, Decimal("1")), Decimal("1")) if candidate.cost else ZERO
    bonus = Decimal("0.5") if closes_gap else ZERO

    return float(effect * weight + bonus - Decimal("0.3") * cost_share)


def shortlist(items: Sequence[Evaluated]) -> List[Evaluated]:
    """At most `max_cards` per template, best engine score first."""
    kept: List[Evaluated] = []
    for template_key in dict.fromkeys(item.template.key for item in items):
        group = sorted((item for item in items if item.template.key == template_key), key=lambda item: -item.score)
        kept.extend(group[: group[0].template.max_cards])
    return kept


def situation(context: TemplateContext) -> str:
    if context.breach_date:
        return (
            f"Cash falls to {context.m(context.base.lowest_balance)} on {day_month(context.base.lowest_balance_date)}, "
            f"below the minimum of {context.m(context.buffer)} the owner wants to keep (worst case {context.m(context.pessimistic.lowest_balance)})."
        )
    return f"No cash gap in the next {context.inputs.horizon_days} days; the balance stays above {context.m(context.buffer)}."


def _other_names(item: Evaluated, items: Sequence[Evaluated], context: TemplateContext) -> Tuple[str, ...]:
    names = {other.candidate.counterparty for other in items if other is not item and other.candidate.counterparty}
    names |= {invoice.counterparty for invoice in context.invoices}
    names |= {payment.counterparty for payment in context.baseline.recurring}
    own = item.candidate.counterparty
    return tuple(sorted(name for name in names if name and name != own))


def _check(item: Evaluated, items: Sequence[Evaluated], context: TemplateContext) -> CheckContext:
    own = (item.candidate.counterparty,) if item.candidate.counterparty else ()
    return CheckContext(
        slots=item.candidate.slots,
        currency=context.currency,
        own_names=own,
        other_names=_other_names(item, items, context),
        extra_forbidden=(
            *item.template.guardrails.extra_forbidden,
            *(() if item.closes_gap else GAP_CLOSED_CLAIMS),
            *(OTHER_PARTY_AGREEMENT_PHRASES if item.template.traits.certainty == CERTAINTY_OWN else ()),
        ),
    )


def _copy_request(item: Evaluated, items: Sequence[Evaluated], context: TemplateContext) -> CopyRequest:
    return CopyRequest(item.dedupe_key, item.template, item.candidate.slots, _check(item, items, context))


def _rank_item(item: Evaluated, context: TemplateContext) -> RankItem:
    template, candidate = item.template, item.candidate
    risk = candidate.relationship_risk or template.traits.relationship_risk
    metrics = {
        "closes the cash gap": YES if item.closes_gap else NO,
        "lowest balance with it": candidate.slots["lowest_balance_with_card"],
        "change of the lowest balance": context.m(item.improvement),
        "cost": context.m(candidate.cost),
        "who decides": {CERTAINTY_OWN: "the owner alone", CERTAINTY_COUNTERPARTY: "the other company must agree"}.get(template.traits.certainty, "the bank must agree"),
        "risk to the relationship": risk,
        "can be undone": YES if template.traits.reversible else NO,
    }
    check = CheckContext(slots={**candidate.slots, **{k: v for k, v in metrics.items()}}, currency=context.currency,
                         own_names=(candidate.counterparty,) if candidate.counterparty else ())
    return RankItem(
        key=item.dedupe_key,
        summary=f"{template.name}: {fill(template.fallback.title, candidate.slots)}",
        metrics=metrics,
        tier=item.tier,
        score=item.score,
        fallback_reason=fallback_reason(item, context),
        check=check,
    )


def fallback_reason(item: Evaluated, context: TemplateContext) -> str:
    certainty = item.template.traits.certainty
    if item.tier == TIER_FREE_CLOSES_GAP:
        return "Free, in your hands, and it closes the gap on its own."
    if item.candidate.cost > ZERO and item.closes_gap:
        return f"Closes the gap for about {context.m(item.candidate.cost)}, if the bank agrees."
    if item.candidate.cost > ZERO:
        return f"Brings money in sooner for about {context.m(item.candidate.cost)}."
    if certainty == CERTAINTY_COUNTERPARTY:
        return "Costs nothing, but the other company has to agree."
    if item.improvement > ZERO:
        return f"Free and in your hands; it lifts your lowest balance by {context.m(item.improvement)}."
    if item.improvement < ZERO:
        return f"Saves money, but your lowest balance drops by {context.m(-item.improvement)}."
    return "Saves money without touching the weeks when cash is tight."


async def _existing(db: AsyncSession, keys: Sequence[str]) -> Dict[str, AgentAction]:
    if not keys:
        return {}
    query = select(AgentAction).where(AgentAction.dedupe_key.in_(list(keys)))
    return {action.dedupe_key: action for action in (await db.execute(query)).scalars().all()}


def _is_open(action: Optional[AgentAction]) -> bool:
    return action is None or action.status == ACTION_STATUS_PENDING


def _template_info(action: Optional[AgentAction]) -> Dict[str, Any]:
    return dict((action.impact_simulation or {}).get(TEMPLATE_KEY) or {}) if action else {}


def _needs_copy(action: Optional[AgentAction], item: Evaluated) -> bool:
    info = _template_info(action)
    return not action or info.get("slots") != item.candidate.slots or info.get("copy_source") == COPY_SOURCE_FALLBACK


def _save(db, live, existing, copies: Dict[str, CardCopy], ranking: Ranking, context: TemplateContext) -> Dict[str, int]:
    created = updated = 0
    position = {key: index + 1 for index, key in enumerate(ranking.order)}

    for item in live:
        action = existing.get(item.dedupe_key)
        copy = copies.get(item.dedupe_key)
        if action is None:
            action = AgentAction(status=ACTION_STATUS_PENDING, execution_mode=EXECUTION_MODE_SIMULATED, dedupe_key=item.dedupe_key)
            db.add(action)
            created += 1
        else:
            updated += 1

        _fill_action(action, item, copy, position.get(item.dedupe_key), ranking, context)

    return {"created": created, "updated": updated}


def _fill_action(action: AgentAction, item: Evaluated, copy: Optional[CardCopy], position, ranking: Ranking, context: TemplateContext) -> None:
    template, candidate = item.template, item.candidate
    info = _template_info(action)

    if copy:
        action.title = copy.fields["title"]
        action.trigger_reason = copy.fields["proposal"]
        action.explanation = copy.fields["explanation"]
        info.update(copy_source=copy.source, copy_violations=copy.violations)

    info.update(
        key=template.key,
        version=template.version,
        goals=list(template.goals),
        slots=candidate.slots,
        rank=position,
        rank_reason=ranking.reasons.get(item.dedupe_key),
        rank_source=ranking.source,
        tier=item.tier,
        engine_score=round(item.score, 4),
        closes_gap=item.closes_gap,
        cost=str(candidate.cost),
    )

    impact = {
        CASH_CHANGES_KEY: [_change(context, change) for change in candidate.changes],
        SWIPE_RIGHT_KEY: template.right_label,
        SWIPE_LEFT_KEY: template.left_label,
        NEXT_SUB_KEY: f"{AGENT_DISPLAY.get(template.agent, DEFAULT_AGENT_DISPLAY)[0]} · {template.name.lower()}",
        PRIORITY_KEY: position or 99,
        "engine_facts": candidate.slots,
        "calculation_source": "card_templates_v1",
        TEMPLATE_KEY: info,
    }
    if template.mail:
        impact[MAIL_KEY] = _mail(template, candidate, context)

    action.agent_type = template.agent
    action.recommended_action = template.key
    action.target_amount = candidate.amount
    action.currency = context.currency
    action.source_type = candidate.source_type
    action.source_id = candidate.source_id[:64]
    action.impact_simulation = impact  # new dict: JSON columns only save on reassignment


def _change(context: TemplateContext, change) -> Dict[str, Any]:
    offset = max(1, (change.on_date - context.as_of).days)
    return {CHANGE_DAY_OFFSET_KEY: offset, CHANGE_AMOUNT_KEY: str(change.amount.quantize(CENT)), CHANGE_LABEL_KEY: change.label}


def _mail(template: CardTemplate, candidate: Candidate, context: TemplateContext) -> Dict[str, Any]:
    to = candidate.counterparty or "Commerzbank relationship manager"
    owner = f"{context.owner_name}, {context.company_name}".strip(", ")
    return {
        "to": to,
        "initials": "".join(part[0] for part in to.split()[:2]).upper(),
        "subject": fill(template.mail.subject, candidate.slots),
        "body": [*(fill(line, candidate.slots) for line in template.mail.lines), f"Kind regards,\n{owner}"],
    }


async def _mark_stale(db: AsyncSession, live_keys: set) -> int:
    """Template cards the agents no longer propose stay in the database (history) but leave the deck."""
    query = select(AgentAction).where(AgentAction.status == ACTION_STATUS_PENDING)
    count = 0
    for action in (await db.execute(query)).scalars().all():
        impact = action.impact_simulation or {}
        if TEMPLATE_KEY not in impact:
            continue
        stale = action.dedupe_key not in live_keys
        if bool(impact.get(STALE_KEY)) != stale:
            action.impact_simulation = {**impact, STALE_KEY: stale}
            count += int(stale)
    return count


# ---------------------------------------------------------------- the deck

async def list_ui_cards(db: AsyncSession) -> List[Dict[str, Any]]:
    """Pending cards in the frontend's DecisionCard format: ranked template cards first, at most DECK_MAX_CARDS of them."""
    context = await load_context(db, None, CARD_HORIZON_DAYS)
    if not context:
        return []

    query = select(AgentAction).where(AgentAction.status == ACTION_STATUS_PENDING).order_by(AgentAction.created_at)
    actions = [action for action in (await db.execute(query)).scalars().all() if not (action.impact_simulation or {}).get(STALE_KEY)]

    templated = deck(sorted((a for a in actions if TEMPLATE_KEY in (a.impact_simulation or {})), key=_rank_key))
    others = sorted((a for a in actions if TEMPLATE_KEY not in (a.impact_simulation or {})), key=lambda a: (a.impact_simulation or {}).get(PRIORITY_KEY, 99))

    return [to_ui_card(action, context, preview_result(context, action)) for action in [*templated, *others]]


def deck(ranked: List[AgentAction]) -> List[AgentAction]:
    """The top DECK_MAX_CARDS cards, plus any card that closes the gap on its own (never cut a working fix)."""
    kept = ranked[:DECK_MAX_CARDS]
    kept += [a for a in ranked[DECK_MAX_CARDS:] if ((a.impact_simulation or {}).get(TEMPLATE_KEY) or {}).get("closes_gap")]
    return kept


def _rank_key(action: AgentAction) -> Tuple[int, int]:
    info = (action.impact_simulation or {}).get(TEMPLATE_KEY) or {}
    return (info.get("rank") or 99, info.get("tier", 9))


def _bars(lows: Tuple[Decimal, ...], scale: Decimal) -> List[int]:
    return [max(BAR_MIN_HEIGHT, int(low / scale * BAR_MAX_HEIGHT)) if scale > 0 else BAR_MIN_HEIGHT for low in lows]


def to_ui_card(action: AgentAction, context: ForecastContext, result: SimulationResult) -> Dict[str, Any]:
    impact = action.impact_simulation or {}
    info = impact.get(TEMPLATE_KEY) or {}
    template = TEMPLATES_BY_KEY.get(info.get("key", ""))
    currency = action.currency
    agent, category, icon, bank_product = AGENT_DISPLAY.get(action.agent_type, DEFAULT_AGENT_DISPLAY)

    before = result.baseline.scenarios[SCENARIO_BASE]
    after = result.simulated.scenarios[SCENARIO_BASE]
    change = result.lowest_balance_change
    breach_after = after.indicators.first_below_buffer_date
    # "I'd swipe right" when the card helps (or saves money) without lowering the lowest balance or the confidence.
    saves_money = bool(template) and GOAL_SAVE_MONEY in template.goals
    says_yes = change >= 0 and result.simulated.confidence >= result.baseline.confidence and (change > 0 or not breach_after or saves_money)

    weeks = weekly_lows(before.days, CARD_WEEKS)
    weeks_after = weekly_lows(after.days, CARD_WEEKS)
    scale = max([*weeks, *weeks_after, context.inputs.safety_buffer, Decimal("1")])
    amount = action.target_amount or Decimal("0")
    hold_above = template.guardrails.hold_to_confirm_above if template else Decimal("10000")

    return {
        "id": str(action.id),
        "backendId": str(action.id),
        "agent": agent,
        "category": category,
        "icon": icon,
        "bankProduct": template.guardrails.bank_product if template else bank_product,
        "autonomy": template.guardrails.autonomy_label if template else "Requires approval",
        "title": action.title,
        "proposal": action.trigger_reason,
        "confidence": int((result.simulated.confidence * HUNDRED).to_integral_value()),
        "recommendation": "right" if says_yes else "left",
        "left": impact.get(SWIPE_LEFT_KEY, "Decline"),
        "right": impact.get(SWIPE_RIGHT_KEY, "Approve"),
        "protects": float(max(change, Decimal("0"))),
        "amount": float(amount),
        "resultLabel": f"{impact.get(SWIPE_RIGHT_KEY, action.title)}{RESULT_SUFFIX}",
        "holdToConfirm": amount > hold_above,
        "followUps": ["scheduleMail", "calendar"] if impact.get(MAIL_KEY) else ["calendar"],
        "mail": impact.get(MAIL_KEY),
        "rank": info.get("rank"),
        "rankReason": info.get("rank_reason"),
        "template": info.get("key"),
        "copySource": info.get("copy_source"),
        "next": {
            "sub": impact.get(NEXT_SUB_KEY, agent),
            "chip": f"{'+' if change >= 0 else ''}{money(change, currency)}",
            "tone": "green" if says_yes else "amber",
        },
        "back": {
            "description": action.explanation,
            "facts": [
                ["Lowest balance now", f"{money(before.indicators.lowest_balance, currency)} · {day_month(before.indicators.lowest_balance_date)}"],
                ["Lowest if approved", f"{money(after.indicators.lowest_balance, currency)} · {day_month(after.indicators.lowest_balance_date)}"],
                ["Safety buffer", money(context.inputs.safety_buffer, currency)],
                ["Buffer if approved", f"broken {day_month(breach_after)}" if breach_after else "holds"],
                ["Confidence", f"{int(result.baseline.confidence * HUNDRED)}% → {int(result.simulated.confidence * HUNDRED)}%"],
            ],
            "weeks": _bars(weeks, scale),
            "weeksIfApproved": _bars(weeks_after, scale),
            "bufferLevel": _bars((context.inputs.safety_buffer,), scale)[0],
            "sources": CARD_SOURCES,
            "questions": list(template.questions) if template else [
                "Where does the confidence come from?",
                "What if I do nothing?",
                "Which payments cause the gap?",
                "Explain it more simply",
            ],
        },
        "engine": {
            "lowest_before": str(before.indicators.lowest_balance),
            "lowest_after": str(after.indicators.lowest_balance),
            "lowest_change": str(change),
            "confidence_before": str(result.baseline.confidence),
            "confidence_after": str(result.simulated.confidence),
            "breach_after": str(breach_after) if breach_after else None,
        },
    }


# ---------------------------------------------------------------- "Ask why"

async def explain_card(db: AsyncSession, action_id, question: str) -> Optional[ExplainActionResponse]:
    """The stored, already checked explanation for the default "why"; other questions go to the model with guardrails."""
    action = await get_action(db, action_id)
    if not action:
        return None

    context = await load_context(db, None, CARD_HORIZON_DAYS)
    facts = explain_facts(action, context) if context else {"card_front": _card_front(action)}

    if _is_default_why(action, question):
        return _response(action, question, _stored_why(action), EXPLAIN_SOURCE_TEMPLATE, facts, "card template")

    deterministic = fallback_answer(facts) or action.explanation
    try:
        answer, source = await answer_question(facts, question, deterministic)
        model = settings.MODEL_NAME or UNKNOWN_MODEL_NAME
        source = RESPONSE_SOURCE_MODEL if source == "model" else source
    except LLMUnavailableError:
        answer, model, source = deterministic, EXPLAIN_FALLBACK_MODEL, RESPONSE_SOURCE_FALLBACK

    return _response(action, question, answer, source, facts, model)


def _is_default_why(action: AgentAction, question: str) -> bool:
    has_template = TEMPLATE_KEY in (action.impact_simulation or {})
    return has_template and question.strip().lower().startswith(WHY_QUESTION_PREFIX)


def _stored_why(action: AgentAction) -> str:
    reason = ((action.impact_simulation or {}).get(TEMPLATE_KEY) or {}).get("rank_reason")
    return f"{action.explanation} {reason}".strip() if reason else action.explanation


def _response(action, question, answer, source, facts, model) -> ExplainActionResponse:
    return ExplainActionResponse(action_id=action.id, model=model, question=question, answer=answer, facts_used=facts, response_source=source)


def _card_front(action: AgentAction) -> Dict[str, Any]:
    impact = action.impact_simulation or {}
    return {"title": action.title, "proposal": action.trigger_reason, "recommended_choice": impact.get(SWIPE_RIGHT_KEY)}


def _percent(value: Decimal) -> int:
    return int((value * HUNDRED).to_integral_value())


def _biggest_outflows(days, start: date, end: date, currency: str, limit: int = 3) -> List[str]:
    drivers = [
        (driver.amount, driver.label, day.day)
        for day in days
        if start <= day.day <= end
        for driver in day.drivers
        if driver.amount < 0
    ]
    drivers.sort(key=lambda item: item[0])
    return [f"{label} {money(amount, currency)} ({day_month(day)})" for amount, label, day in drivers[:limit]]


def explain_facts(action: AgentAction, context: ForecastContext) -> Dict[str, Any]:
    currency = context.account.currency
    inputs = context.inputs
    own = card_changes(action, inputs.as_of)
    others = [*context.known_events, *(change for decision in context.decisions if decision.action.id != action.id for change in decision.changes)]

    result = preview_result(context, action)
    before = result.baseline.scenarios[SCENARIO_BASE]
    after = result.simulated.scenarios[SCENARIO_BASE]
    grid = confidence_grid(inputs, [*others, *own])
    model = result.baseline.revenue_model
    lowest_day = before.indicators.lowest_balance_date

    return {
        "card_front": _card_front(action),
        "engine": {
            "forecast_start": str(inputs.as_of),
            "balance_today": money(inputs.opening_balance, currency),
            "safety_buffer": money(inputs.safety_buffer, currency),
            "horizon_days": inputs.horizon_days,
            "lowest_balance_without_card": f"{money(before.indicators.lowest_balance, currency)} on {lowest_day}",
            "lowest_balance_with_card": f"{money(after.indicators.lowest_balance, currency)} on {after.indicators.lowest_balance_date}",
            "buffer_broken_without_card": str(before.indicators.first_below_buffer_date) if before.indicators.first_below_buffer_date else "never",
            "buffer_broken_with_card": str(after.indicators.first_below_buffer_date) if after.indicators.first_below_buffer_date else "never",
            "confidence_without_card_percent": _percent(result.baseline.confidence),
            "confidence_with_card_percent": _percent(result.simulated.confidence),
            "confidence_method": CONFIDENCE_METHOD.format(
                steps=len(grid), low=_percent(grid[0].revenue_factor), high=_percent(grid[-1].revenue_factor), days=inputs.horizon_days
            ),
            "revenue_scenarios_with_card": [
                {"revenue_level_percent": _percent(point.revenue_factor), "lowest_balance": money(point.lowest_balance, currency), "keeps_buffer": point.keeps_buffer}
                for point in grid
            ],
            "card_cash_changes": [{"date": str(change.on_date), "amount": money(change.amount, currency), "label": change.label} for change in own],
            "biggest_outflows_near_lowest": _biggest_outflows(before.days, lowest_day - timedelta(days=7), lowest_day, currency, 4),
            "recurring_payments": [
                f"{payment.counterparty}: {money(payment.amount, currency)} every {payment.interval_months} month(s) on day {payment.day_of_month}"
                for payment in sorted(result.baseline.recurring, key=lambda item: item.amount)[:6]
            ],
            "revenue_model": {
                "average_revenue_per_weekday_mon_to_sun": [money(value, currency) for value in model.weekday_inflow],
                "variable_costs_percent_of_revenue": _percent(model.variable_cost_ratio),
                "weekly_revenue_volatility_percent": _percent(model.volatility),
            },
            "late_payers": [
                f"{late.counterparty} pays {late.typical_delay_days} days late on average ({late.paid_invoices_seen} invoices)"
                for late in context.late_payers
            ],
        },
        "card_specific_facts": (action.impact_simulation or {}).get("engine_facts", {}),
    }


def fallback_answer(facts: Dict[str, Any]) -> Optional[str]:
    engine = facts.get("engine")
    if not engine:
        return None

    grid = engine["revenue_scenarios_with_card"]
    safe = sum(1 for point in grid if point["keeps_buffer"])
    return (
        f"Confidence {engine['confidence_with_card_percent']}% (without this decision {engine['confidence_without_card_percent']}%): "
        f"the engine tried {len(grid)} revenue levels from {grid[0]['revenue_level_percent']}% to {grid[-1]['revenue_level_percent']}% "
        f"of the expected revenue, and in {safe} of them the balance stays above the {engine['safety_buffer']} buffer. "
        f"Lowest balance: {engine['lowest_balance_without_card']} now, {engine['lowest_balance_with_card']} with this decision. "
        f"Buffer broken: {engine['buffer_broken_without_card']} now, {engine['buffer_broken_with_card']} with it."
    )
