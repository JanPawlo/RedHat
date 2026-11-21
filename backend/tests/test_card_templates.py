import re
from decimal import Decimal

from app.const.card_templates import GOAL_CLOSE_GAP, TIER_COSTLY
from app.const.forecast import SCENARIO_BASE
from app.managers.card_manager import _copy_request
from app.services.card_guardrails import check_card
from app.services.card_templates import REGISTRY, TEMPLATES_BY_KEY, active_goals, engine_gap_report, fill
from app.services.card_writer import fallback_copy
from tests.card_demo import demo_context, demo_shortlist

PLACEHOLDER = re.compile(r"\{(\w+)\}")
PROTECTED = ("tax office", "krankenkasse", "salary", "vincenzo amalfi", "yusuf", "rosa pavese", "vanessa")


def test_registry_keys_are_unique_and_complete():
    keys = [template.key for template in REGISTRY]
    assert len(keys) == len(set(keys))
    for template in REGISTRY:
        assert template.engine_inputs, template.key
        assert template.brief and template.questions and template.right_label and template.left_label
        assert template.max_cards >= 1


def test_demo_data_triggers_every_template():
    _, items = demo_shortlist()
    assert {item.template.key for item in items} == set(TEMPLATES_BY_KEY) - {"term_deposit"}
    assert GOAL_CLOSE_GAP in active_goals(demo_context())


def test_fallback_placeholders_exist_in_slots():
    _, items = demo_shortlist()
    for item in items:
        fallback = item.template.fallback
        for text in (fallback.title, fallback.proposal, fallback.explanation):
            for key in PLACEHOLDER.findall(text):
                if key in ("offer", "habit"):  # optional sentences
                    continue
                assert key in item.candidate.slots, f"{item.template.key}: {{{key}}} missing"


def test_must_mention_slots_exist():
    _, items = demo_shortlist()
    for item in items:
        guardrails = item.template.guardrails
        for key in (*guardrails.must_mention, *guardrails.title_must_mention):
            assert key in item.candidate.slots, f"{item.template.key}: {key}"


def test_every_fallback_card_passes_its_own_guardrails():
    context, items = demo_shortlist()
    for item in items:
        request = _copy_request(item, items, context)
        guardrails = item.template.guardrails
        problems = check_card(fallback_copy(request), request.check, guardrails.must_mention, guardrails.title_must_mention, guardrails.required_phrases)
        assert not any(problems.values()), (item.template.key, problems)


def test_no_candidate_creates_a_new_gap_and_gap_cards_help():
    _, items = demo_shortlist()
    for item in items:
        before = item.result.baseline.scenarios[SCENARIO_BASE].indicators
        after = item.result.simulated.scenarios[SCENARIO_BASE].indicators
        assert not (after.first_below_buffer_date and not before.first_below_buffer_date)
        if item.template.goals == (GOAL_CLOSE_GAP,) and not item.template.allow_zero_effect:
            assert item.improvement > 0, item.template.key


def test_credit_covers_the_worst_case_and_is_ranked_last_tier():
    context, items = demo_shortlist()
    credit = next(item for item in items if item.template.key == "take_credit")
    assert credit.candidate.amount >= context.buffer - context.pessimistic.lowest_balance
    assert credit.candidate.amount % Decimal("1000") == 0
    assert credit.closes_gap
    assert credit.tier == TIER_COSTLY
    assert len([item for item in items if item.template.key == "take_credit"]) == 1  # cheapest product only


def test_protected_payments_are_never_moved_or_cancelled():
    _, items = demo_shortlist()
    for item in items:
        if item.template.key in ("negotiate_extension", "cancel_subscription"):
            name = (item.candidate.counterparty or "").lower()
            assert not any(marker in name for marker in PROTECTED), name


def test_delay_card_uses_the_planned_oven_and_moves_it_later():
    _, items = demo_shortlist()
    delay = next(item for item in items if item.template.key == "delay_planned_investment")
    first, second = delay.candidate.changes
    assert first.amount == Decimal("8500.00") and second.amount == Decimal("-8500.00")
    assert second.on_date > first.on_date


def test_fill_leaves_missing_optional_slots_readable():
    assert fill("Hi {name}. {missing}", {"name": "Jan"}) == "Hi Jan."


def test_engine_gap_report_names_known_gaps():
    gaps = engine_gap_report()
    inputs = {name for _, name, _ in gaps}
    assert "Overdue invoices in the forecast" in inputs
    assert "Planned purchases with dates" in inputs
    assert all(why for _, _, why in gaps)
